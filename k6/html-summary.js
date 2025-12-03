import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

export function handleSummary(data) {
  return {
    'report.html': htmlReport(data),
    'summary.txt': textSummary(data, { indent: ' ', enableColors: true })
  };
}
