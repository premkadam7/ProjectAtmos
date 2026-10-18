import { test } from 'node:test';
import assert from 'node:assert/strict';
import { aqiToPm25, pm25ToAqi, wardEstimate } from './spatial.js';

test('interpolate concentrations before converting to AQI', () => {
  const result = wardEstimate({lat:28,lon:77}, [
    {lat:28,lon:76.99,pm25:30}, {lat:28,lon:77.01,pm25:120},
  ]);
  assert.ok(Math.abs(result.pm25-75)<1e-8);
  assert.ok(Math.abs(result.aqi-150)<1e-8); // average of AQIs would incorrectly be 175
});
test('identical inputs remain identical; remote wards have no estimate', () => {
  const inputs=[{lat:28,lon:77,pm25:60},{lat:28.01,lon:77,pm25:60}];
  assert.equal(wardEstimate({lat:28,lon:77},inputs).aqi,100);
  assert.equal(wardEstimate({lat:29,lon:78},inputs).aqi,null);
});
test('concentration round trips through Indian breakpoints', () => {
  for (const pm of [0,30,60,75,90,120,149.5,250,500]) {
    assert.ok(Math.abs(aqiToPm25(pm25ToAqi(pm))-pm)<1e-8);
  }
});
