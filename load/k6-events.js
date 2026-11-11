import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = {
  scenarios: { ingest: { executor: 'constant-vus', vus: 10, duration: '45s' } },
  thresholds: { http_req_failed: ['rate<0.01'], http_req_duration: ['p(95)<750'] },
};
const url = __ENV.BASE_URL || 'http://localhost:8091';
const tenant = __ENV.TENANT || 'acme';
export default function () {
  if (!__ENV.JWT) throw new Error('Set JWT to a valid short-lived test token');
  const key = `load-${__VU}-${__ITER}`;
  const response = http.post(`${url}/v1/events`, JSON.stringify({
    tenant_id: tenant, event_type: 'order.paid', metadata: { amount: 120, source: 'k6' },
  }), { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${__ENV.JWT}`,
                    'Idempotency-Key': key } });
  check(response, { 'accepted': (r) => r.status === 202 });
  sleep(0.25);
}
