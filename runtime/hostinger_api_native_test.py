"""
Unit tests for Hostinger API Native SDK.
Run with: python3 -m pytest hostinger_api_native_test.py -v
Or: python3 hostinger_api_native_test.py
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure the runtime module is importable
sys.path.insert(0, "/mnt/agents/MAGNATRIX-OS/runtime")

from hostinger_api_native import (
    HostingerClient,
    HostingerError,
    HostingerAuthError,
    HostingerRateLimitError,
    HostingerNotFoundError,
    HostingerValidationError,
    HostingerServerError,
    HostingerConflictError,
    HostingerPermissionError,
    RequestBuilder,
    BaseResponse,
    Pagination,
    Meta,
    BillingAPI,
    DNSAPI,
    DomainsAPI,
    HostingAPI,
    VPSAPI,
    ReachAPI,
    HostingerKernel,
    CatalogItem,
    PaymentMethod,
    Subscription,
    DNSRecord,
    DNSZone,
    DNSSnapshot,
    DomainInfo,
    DomainAvailability,
    WhoisInfo,
    DomainForward,
    Datacenter,
    Website,
    HostingOrderRequest,
    HostingOrder,
    VPSPlan,
    VM,
    VPSAction,
    Backup,
    Snapshot,
    FirewallRule,
    FirewallConfig,
    SSHKey,
    OSTemplate,
    PTRRecord,
    MalwareScanResult,
    DockerContainer,
    PostInstallScript,
    RecoveryConsole,
    Contact,
    Profile,
    Segment,
)


class TestHostingerClient(unittest.TestCase):
    def test_client_init(self):
        c = HostingerClient("token123")
        self.assertEqual(c.api_token, "token123")
        self.assertFalse(c._use_httpx)

    def test_client_repr(self):
        c = HostingerClient("t")
        self.assertIn("HostingerClient", repr(c))

    def test_default_headers(self):
        c = HostingerClient("tok")
        h = c._default_headers()
        self.assertEqual(h["Authorization"], "Bearer tok")
        self.assertEqual(h["Content-Type"], "application/json")

    def test_should_retry_429(self):
        c = HostingerClient("t")
        self.assertTrue(c._should_retry(429, "GET"))

    def test_should_retry_500(self):
        c = HostingerClient("t")
        self.assertTrue(c._should_retry(500, "GET"))

    def test_should_not_retry_422_post(self):
        c = HostingerClient("t")
        self.assertFalse(c._should_retry(422, "POST"))

    def test_jitter_delay(self):
        c = HostingerClient("t")
        d = c._jitter_delay(1)
        self.assertGreater(d, 0)
        self.assertLessEqual(d, 60)

    def test_map_exception_401(self):
        c = HostingerClient("t")
        e = c._map_exception(401, '{"message":"bad"}', {})
        self.assertIsInstance(e, HostingerAuthError)

    def test_map_exception_429(self):
        c = HostingerClient("t")
        e = c._map_exception(429, '{"message":"rate","retryAfter":5}', {})
        self.assertIsInstance(e, HostingerRateLimitError)
        self.assertEqual(e.retry_after, 5)

    def test_map_exception_404(self):
        c = HostingerClient("t")
        e = c._map_exception(404, "", {})
        self.assertIsInstance(e, HostingerNotFoundError)

    def test_map_exception_422(self):
        c = HostingerClient("t")
        e = c._map_exception(422, '{"errors":{"name":["required"]}}', {})
        self.assertIsInstance(e, HostingerValidationError)

    def test_map_exception_409(self):
        c = HostingerClient("t")
        e = c._map_exception(409, "", {})
        self.assertIsInstance(e, HostingerConflictError)

    def test_map_exception_403(self):
        c = HostingerClient("t")
        e = c._map_exception(403, "", {})
        self.assertIsInstance(e, HostingerPermissionError)

    def test_map_exception_500(self):
        c = HostingerClient("t")
        e = c._map_exception(500, "", {})
        self.assertIsInstance(e, HostingerServerError)

    def test_request_builder(self):
        c = HostingerClient("t")
        rb = c.request().get("/test").query(page=1)
        self.assertEqual(rb._method, "GET")
        self.assertEqual(rb._path, "/test")
        self.assertEqual(rb._query, {"page": 1})

    def test_paginate_empty(self):
        c = HostingerClient("t")
        with patch.object(c, "_request") as mock_req:
            mock_req.return_value = BaseResponse(data=[])
            result = c.paginate("GET", "/items")
            self.assertEqual(result, [])


class TestDataclasses(unittest.TestCase):
    def test_catalog_item_repr(self):
        ci = CatalogItem(id=1, name="VPS", price=5.99)
        self.assertIn("VPS", repr(ci))

    def test_vm_repr(self):
        vm = VM(id=1, name="web1", ipv4="1.2.3.4")
        self.assertIn("web1", repr(vm))

    def test_dns_record_repr(self):
        r = DNSRecord(name="www", type="A", value="1.2.3.4")
        self.assertIn("A", repr(r))

    def test_firewall_rule_repr(self):
        fr = FirewallRule(id=1, protocol="tcp", port_range="80")
        self.assertIn("tcp", repr(fr))

    def test_pagination_has_next(self):
        p = Pagination(current_page=1, total_pages=2, next_page_url="/next")
        self.assertTrue(p.has_next())

    def test_pagination_has_no_next(self):
        p = Pagination(current_page=2, total_pages=2)
        self.assertFalse(p.has_next())

    def test_base_response_repr(self):
        br = BaseResponse(data=[1, 2, 3], status_code=200)
        self.assertIn("List[3]", repr(br))


class TestServiceAPIs(unittest.TestCase):
    def setUp(self):
        self.client = HostingerClient("test-token")

    def test_billing_api_repr(self):
        api = BillingAPI(self.client)
        self.assertEqual(repr(api), "BillingAPI()")

    def test_dns_api_repr(self):
        api = DNSAPI(self.client)
        self.assertEqual(repr(api), "DNSAPI()")

    def test_domains_api_repr(self):
        api = DomainsAPI(self.client)
        self.assertEqual(repr(api), "DomainsAPI()")

    def test_hosting_api_repr(self):
        api = HostingAPI(self.client)
        self.assertEqual(repr(api), "HostingAPI()")

    def test_vps_api_repr(self):
        api = VPSAPI(self.client)
        self.assertEqual(repr(api), "VPSAPI()")

    def test_reach_api_repr(self):
        api = ReachAPI(self.client)
        self.assertEqual(repr(api), "ReachAPI()")


class TestHostingerKernel(unittest.TestCase):
    def test_kernel_init(self):
        k = HostingerKernel("tok")
        self.assertIsNotNone(k.client)
        self.assertIsNotNone(k.billing)
        self.assertIsNotNone(k.dns)
        self.assertIsNotNone(k.domains)
        self.assertIsNotNone(k.hosting)
        self.assertIsNotNone(k.vps)
        self.assertIsNotNone(k.reach)

    def test_kernel_register_hooks(self):
        k = HostingerKernel("tok")
        k.register_hook("vm_created", lambda **kw: None)
        self.assertEqual(len(k._hooks["vm_created"]), 1)

    def test_kernel_layer_register(self):
        k = HostingerKernel("tok")
        k.register_layer7().register_layer5().register_layer11(15)
        self.assertTrue(k._layer7_registered)
        self.assertTrue(k._layer5_registered)
        self.assertTrue(k._layer11_registered)

    def test_kernel_repr(self):
        k = HostingerKernel("tok")
        self.assertIn("HostingerKernel", repr(k))


class TestHelpers(unittest.TestCase):
    def test_to_snake(self):
        from hostinger_api_native import _to_snake
        self.assertEqual(_to_snake("camelCase"), "camel_case")
        self.assertEqual(_to_snake("XMLParser"), "xml_parser")

    def test_map_camel_dict(self):
        from hostinger_api_native import _map_camel_dict
        d = {"userName": "treas", "contactInfo": {"emailAddress": "a@b.c"}}
        m = _map_camel_dict(d)
        self.assertEqual(m["user_name"], "treas")
        self.assertEqual(m["contact_info"]["email_address"], "a@b.c")

    def test_serialize_body_dict(self):
        from hostinger_api_native import _serialize_body
        b = _serialize_body({"a": 1})
        self.assertEqual(b, b'{"a": 1}')

    def test_serialize_body_none(self):
        from hostinger_api_native import _serialize_body
        self.assertIsNone(_serialize_body(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
