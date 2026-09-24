import os
import ssl
import time
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import requests
import urllib3
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from backend.models.transition import UploadedDocument

logger = logging.getLogger("kt_planner.external_extraction")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ResilientTLSAdapter(HTTPAdapter):
    """
    Custom HTTPAdapter configuring SSLContext with OP_IGNORE_UNEXPECTED_EOF
    to prevent OpenSSL 3.0+ from aborting with SSLEOFError when remote Azure/proxy
    terminates TCP connection without sending TLS close_notify.
    """
    def __init__(self, ssl_context: Optional[ssl.SSLContext] = None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)


def _build_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    # Suppress OpenSSL 3.0+ SSLEOFError when server closes TCP without TLS close_notify
    if hasattr(ssl, "OP_IGNORE_UNEXPECTED_EOF"):
        ctx.options |= ssl.OP_IGNORE_UNEXPECTED_EOF
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def create_resilient_session(total_retries: int = 3, backoff: float = 1.5) -> requests.Session:
    ctx = _build_ssl_context()
    # Explicitly set allowed_methods=None so urllib3 retries POST requests on transient drops
    retries = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        backoff_factor=backoff,
        allowed_methods=None,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = ResilientTLSAdapter(ssl_context=ctx, max_retries=retries)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def warm_up_endpoint(url: str, timeout: int = 15) -> bool:
    """
    Sends a lightweight GET request to the Azure host to wake up cold containers
    and negotiate initial TLS parameters before sending heavy multipart payloads.
    """
    try:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        warmup_urls = [f"{base_url}/docs", f"{base_url}/openapi.json", base_url]
        session = create_resilient_session(total_retries=1, backoff=0.5)
        for target in warmup_urls:
            try:
                r = session.get(target, timeout=timeout, verify=False, headers={"Connection": "close"})
                if r.status_code in (200, 404):
                    logger.info(f"Endpoint warmup probe successful on {target} (status {r.status_code})")
                    return True
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"Warmup probe skipped/failed: {e}")
    return False


def call_external_extraction_api(
    external_api_url: str,
    docs: List[UploadedDocument],
    timeout_seconds: int = 600,
    max_outer_attempts: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Robustly sends uploaded documents to the external extraction API with:
    1. In-memory binary file payloads (ensuring safe rewinding on HTTP retries).
    2. Resilient TLS adapter with OP_IGNORE_UNEXPECTED_EOF.
    3. Retries configured for POST requests.
    4. Connection: close to avoid stale keep-alive sockets dropped by Azure ARR.
    5. Outer retry loop with exponential backoff and container warmup probe.
    """
    if not external_api_url or not docs:
        return None

    # Load all files into memory so retries are safe
    files_to_send = []
    for doc in docs:
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                with open(doc.file_path, "rb") as f:
                    content = f.read()
                mime = doc.mime_type or "application/pdf"
                if doc.file_name.lower().endswith(".pdf"):
                    mime = "application/pdf"
                elif doc.file_name.lower().endswith(".xlsx"):
                    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                files_to_send.append(("files", (doc.file_name, content, mime)))
            except Exception as read_err:
                logger.error(f"Failed to read file {doc.file_path} for extraction: {read_err}")

    if not files_to_send:
        logger.warning("No valid document files found to send to external extraction API.")
        return None

    logger.info(f"Prepared {len(files_to_send)} file(s) for extraction to {external_api_url}")

    for attempt in range(1, max_outer_attempts + 1):
        session = create_resilient_session(total_retries=2, backoff=1.5)
        try:
            logger.info(f"Calling external extraction API (attempt {attempt}/{max_outer_attempts})...")
            resp = session.post(
                external_api_url,
                files=files_to_send,
                headers={"Connection": "close"},
                timeout=timeout_seconds,
                verify=False,
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.info(
                    f"External API extraction successful! Project: '{data.get('project_name')}', "
                    f"Category: '{data.get('project_category')}', "
                    f"Applications: {len(data.get('applications', []))}"
                )
                return data
            else:
                logger.error(
                    f"External API returned HTTP {resp.status_code} (attempt {attempt}/{max_outer_attempts}): {resp.text[:500]}"
                )
                if attempt < max_outer_attempts:
                    sleep_time = attempt * 3
                    logger.info(f"Retrying extraction in {sleep_time}s...")
                    time.sleep(sleep_time)
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_err:
            logger.warning(
                f"External extraction attempt {attempt}/{max_outer_attempts} failed with connection/SSL error: {conn_err}"
            )
            if attempt < max_outer_attempts:
                sleep_time = attempt * 3
                logger.info(f"Waking up endpoint and retrying in {sleep_time}s...")
                warm_up_endpoint(external_api_url, timeout=15)
                time.sleep(sleep_time)
            else:
                logger.error(f"All {max_outer_attempts} attempts to external extraction API failed.")
        except Exception as e:
            logger.error(f"Unexpected exception during external extraction attempt {attempt}: {e}", exc_info=True)
            if attempt < max_outer_attempts:
                time.sleep(attempt * 2)
        finally:
            try:
                session.close()
            except Exception:
                pass

    return None

