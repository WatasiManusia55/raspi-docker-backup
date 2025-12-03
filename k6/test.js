import http from 'k6/http';
import { check, sleep } from 'k6';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

export const options = {
  stages: [
    { duration: '10s', target: 10 },   // warmup
    { duration: '20s', target: 20 },   // naik pelan
    { duration: '20s', target: 50 },   // mulai beban sedang
    { duration: '20s', target: 80 },   // load berat
    { duration: '20s', target: 100 },  // max load
    { duration: '20s', target: 0 },    // cool down
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(90)<3000'], // P90 harus <3 detik (lebih masuk akal)
  },
};

export default function () {
  const res = http.get("https://pbl-tmj5a.siling-ai.my.id/");
  check(res, {
    "status 200": (r) => r.status === 200,
  });
  sleep(1);
}

export function handleSummary(data) {
  return {
    "report.html": htmlReport(data),
  };
}
