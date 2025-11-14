/**
 * Load Test for ML Service API
 * Run with: k6 run load_test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const predictionLatency = new Trend('prediction_latency');
const successfulPredictions = new Counter('successful_predictions');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 200 },  // Spike to 200 users
    { duration: '5m', target: 200 },  // Stay at 200 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<200', 'p(99)<500'],  // 95% under 200ms, 99% under 500ms
    'http_req_failed': ['rate<0.01'],                  // Error rate under 1%
    'errors': ['rate<0.01'],
  },
};

// Test data
const API_BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-api-key';

const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
};

const sampleFeatures = {
  MSSubClass: 60,
  MSZoning: 'RL',
  LotArea: 8450,
  LotShape: 'Reg',
  LandContour: 'Lvl',
  Utilities: 'AllPub',
  LotConfig: 'Inside',
  LandSlope: 'Gtl',
  Neighborhood: 'CollgCr',
  Condition1: 'Norm',
  BldgType: '1Fam',
};

// Generate random variations of features
function generateFeatures() {
  return {
    ...sampleFeatures,
    LotArea: Math.floor(Math.random() * 20000) + 5000,
    MSSubClass: Math.floor(Math.random() * 100) + 20,
  };
}

export default function () {
  // Test 1: Single prediction
  const predictionPayload = JSON.stringify({
    model_name: 'house-price-v2',
    features: generateFeatures(),
    options: {
      include_explanation: false,
      include_confidence: true,
    },
  });

  const predictionResponse = http.post(
    `${API_BASE_URL}/v1/predict`,
    predictionPayload,
    { headers }
  );

  const predictionSuccess = check(predictionResponse, {
    'prediction status is 200': (r) => r.status === 200,
    'prediction has value': (r) => {
      const body = JSON.parse(r.body);
      return body.prediction && body.prediction.value > 0;
    },
    'prediction latency < 200ms': (r) => r.timings.duration < 200,
  });

  errorRate.add(!predictionSuccess);
  predictionLatency.add(predictionResponse.timings.duration);

  if (predictionSuccess) {
    successfulPredictions.add(1);
  }

  // Test 2: Health check (10% of requests)
  if (Math.random() < 0.1) {
    const healthResponse = http.get(`${API_BASE_URL}/health`, { headers });

    check(healthResponse, {
      'health status is 200': (r) => r.status === 200,
      'health check is healthy': (r) => {
        const body = JSON.parse(r.body);
        return body.status === 'healthy' || body.status === 'degraded';
      },
    });
  }

  // Test 3: List models (5% of requests)
  if (Math.random() < 0.05) {
    const modelsResponse = http.get(`${API_BASE_URL}/v1/models`, { headers });

    check(modelsResponse, {
      'models status is 200': (r) => r.status === 200,
      'models list not empty': (r) => {
        const body = JSON.parse(r.body);
        return body.models && body.models.length > 0;
      },
    });
  }

  // Think time
  sleep(Math.random() * 2 + 1); // 1-3 seconds
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'load_test_results.json': JSON.stringify(data),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;

  let summary = '\n';
  summary += `${indent}Execution Summary:\n`;
  summary += `${indent}  Scenarios: ${data.root_group.checks.length}\n`;
  summary += `${indent}  Total Requests: ${data.metrics.http_reqs.values.count}\n`;
  summary += `${indent}  Failed Requests: ${data.metrics.http_req_failed.values.rate * 100}%\n`;
  summary += `${indent}\n`;
  summary += `${indent}Response Times:\n`;
  summary += `${indent}  Average: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
  summary += `${indent}  P50: ${data.metrics.http_req_duration.values['p(50)'].toFixed(2)}ms\n`;
  summary += `${indent}  P95: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
  summary += `${indent}  P99: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n`;
  summary += `${indent}  Max: ${data.metrics.http_req_duration.values.max.toFixed(2)}ms\n`;
  summary += `${indent}\n`;
  summary += `${indent}Throughput:\n`;
  summary += `${indent}  RPS: ${data.metrics.http_reqs.values.rate.toFixed(2)}\n`;

  return summary;
}
