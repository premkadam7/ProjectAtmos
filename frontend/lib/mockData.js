export const USE_MOCK = false;

export const mockHealth = {
  status: "ok",
  version: "0.1.0",
  timestamp: "2026-07-03T10:00:00.000000"
};

export const mockForecast = {
  city: "delhi",
  generated_at: "2026-07-03T10:00:00Z",
  total_wards: 250,
  city_avg_aqi: 247,
  worst_ward: "anand_vihar",
  best_ward: "lodhi_garden",
  wards: [
    { ward_id: "anand_vihar", ward_name: "Anand Vihar", lat: 28.6469, lon: 77.3161, current_aqi: 389, forecast_aqi_24h: 410, forecast_aqi_48h: 375, forecast_aqi_72h: 340, trend: "worsening", cigarette_equivalent: 8.2 },
    { ward_id: "wazirpur", ward_name: "Wazirpur", lat: 28.6928, lon: 77.1678, current_aqi: 356, forecast_aqi_24h: 370, forecast_aqi_48h: 345, forecast_aqi_72h: 310, trend: "worsening", cigarette_equivalent: 7.5 },
    { ward_id: "rohini_sector_7", ward_name: "Rohini Sector 7", lat: 28.7369, lon: 77.0656, current_aqi: 334, forecast_aqi_24h: 350, forecast_aqi_48h: 320, forecast_aqi_72h: 290, trend: "stable", cigarette_equivalent: 7.1 },
    { ward_id: "dwarka", ward_name: "Dwarka", lat: 28.5921, lon: 77.0460, current_aqi: 312, forecast_aqi_24h: 295, forecast_aqi_48h: 280, forecast_aqi_72h: 260, trend: "improving", cigarette_equivalent: 6.6 },
    { ward_id: "shahdara", ward_name: "Shahdara", lat: 28.6727, lon: 77.2945, current_aqi: 298, forecast_aqi_24h: 310, forecast_aqi_48h: 295, forecast_aqi_72h: 275, trend: "stable", cigarette_equivalent: 6.3 },
    { ward_id: "karol_bagh", ward_name: "Karol Bagh", lat: 28.6513, lon: 77.1904, current_aqi: 267, forecast_aqi_24h: 280, forecast_aqi_48h: 265, forecast_aqi_72h: 245, trend: "stable", cigarette_equivalent: 5.6 },
    { ward_id: "connaught_place", ward_name: "Connaught Place", lat: 28.6315, lon: 77.2167, current_aqi: 201, forecast_aqi_24h: 215, forecast_aqi_48h: 198, forecast_aqi_72h: 185, trend: "stable", cigarette_equivalent: 4.2 },
    { ward_id: "vasant_kunj", ward_name: "Vasant Kunj", lat: 28.5218, lon: 77.1577, current_aqi: 145, forecast_aqi_24h: 138, forecast_aqi_48h: 130, forecast_aqi_72h: 125, trend: "improving", cigarette_equivalent: 3.1 },
    { ward_id: "lodhi_garden", ward_name: "Lodhi Garden", lat: 28.5931, lon: 77.2197, current_aqi: 98, forecast_aqi_24h: 92, forecast_aqi_48h: 88, forecast_aqi_72h: 85, trend: "improving", cigarette_equivalent: 2.1 },
    { ward_id: "saket", ward_name: "Saket", lat: 28.5245, lon: 77.2066, current_aqi: 178, forecast_aqi_24h: 185, forecast_aqi_48h: 172, forecast_aqi_72h: 160, trend: "stable", cigarette_equivalent: 3.8 },
  ]
};

export const mockWardDetail = {
  ward_id: "rohini_sector_7",
  ward_name: "Rohini Sector 7",
  city: "delhi",
  generated_at: "2026-07-02T00:00:00Z",
  current_aqi: 245.0,
  current_pm25: 115.5,
  cigarette_equivalent: 5.2,
  hourly: [
    { timestamp: "2026-07-02T00:00:00Z", aqi: 250.0, pm25: 120.0, pm10: 200.0, aqi_low: 235.0, aqi_high: 270.0 },
    { timestamp: "2026-07-02T01:00:00Z", aqi: 248.0, pm25: 118.5, pm10: 198.0, aqi_low: 232.0, aqi_high: 268.0 },
    { timestamp: "2026-07-02T02:00:00Z", aqi: 242.0, pm25: 115.0, pm10: 195.0, aqi_low: 228.0, aqi_high: 260.0 },
    { timestamp: "2026-07-02T03:00:00Z", aqi: 238.0, pm25: 112.0, pm10: 190.0, aqi_low: 224.0, aqi_high: 255.0 },
    { timestamp: "2026-07-02T04:00:00Z", aqi: 235.0, pm25: 110.0, pm10: 188.0, aqi_low: 220.0, aqi_high: 252.0 },
    { timestamp: "2026-07-02T05:00:00Z", aqi: 230.0, pm25: 108.0, pm10: 185.0, aqi_low: 215.0, aqi_high: 248.0 },
    { timestamp: "2026-07-02T06:00:00Z", aqi: 240.0, pm25: 114.0, pm10: 192.0, aqi_low: 225.0, aqi_high: 258.0 },
    { timestamp: "2026-07-02T07:00:00Z", aqi: 255.0, pm25: 122.0, pm10: 205.0, aqi_low: 238.0, aqi_high: 275.0 },
    { timestamp: "2026-07-02T08:00:00Z", aqi: 270.0, pm25: 130.0, pm10: 218.0, aqi_low: 252.0, aqi_high: 292.0 },
    { timestamp: "2026-07-02T09:00:00Z", aqi: 280.0, pm25: 135.0, pm10: 225.0, aqi_low: 262.0, aqi_high: 302.0 },
    { timestamp: "2026-07-02T10:00:00Z", aqi: 285.0, pm25: 137.0, pm10: 228.0, aqi_low: 268.0, aqi_high: 305.0 },
    { timestamp: "2026-07-02T11:00:00Z", aqi: 282.0, pm25: 136.0, pm10: 226.0, aqi_low: 265.0, aqi_high: 302.0 },
    { timestamp: "2026-07-02T12:00:00Z", aqi: 275.0, pm25: 132.0, pm10: 220.0, aqi_low: 258.0, aqi_high: 295.0 },
    { timestamp: "2026-07-02T13:00:00Z", aqi: 268.0, pm25: 128.0, pm10: 215.0, aqi_low: 250.0, aqi_high: 288.0 },
    { timestamp: "2026-07-02T14:00:00Z", aqi: 260.0, pm25: 125.0, pm10: 210.0, aqi_low: 242.0, aqi_high: 280.0 },
    { timestamp: "2026-07-02T15:00:00Z", aqi: 255.0, pm25: 122.0, pm10: 206.0, aqi_low: 238.0, aqi_high: 275.0 },
    { timestamp: "2026-07-02T16:00:00Z", aqi: 258.0, pm25: 124.0, pm10: 208.0, aqi_low: 240.0, aqi_high: 278.0 },
    { timestamp: "2026-07-02T17:00:00Z", aqi: 265.0, pm25: 127.0, pm10: 213.0, aqi_low: 248.0, aqi_high: 285.0 },
    { timestamp: "2026-07-02T18:00:00Z", aqi: 272.0, pm25: 131.0, pm10: 219.0, aqi_low: 255.0, aqi_high: 292.0 },
    { timestamp: "2026-07-02T19:00:00Z", aqi: 268.0, pm25: 128.0, pm10: 215.0, aqi_low: 250.0, aqi_high: 288.0 },
    { timestamp: "2026-07-02T20:00:00Z", aqi: 260.0, pm25: 125.0, pm10: 210.0, aqi_low: 242.0, aqi_high: 280.0 },
    { timestamp: "2026-07-02T21:00:00Z", aqi: 252.0, pm25: 120.0, pm10: 203.0, aqi_low: 235.0, aqi_high: 272.0 },
    { timestamp: "2026-07-02T22:00:00Z", aqi: 245.0, pm25: 117.0, pm10: 198.0, aqi_low: 228.0, aqi_high: 265.0 },
    { timestamp: "2026-07-02T23:00:00Z", aqi: 240.0, pm25: 114.0, pm10: 194.0, aqi_low: 224.0, aqi_high: 258.0 },
  ]
};

export const mockBlame = {
  ward_id: "rohini_sector_7",
  ward_name: "Rohini Sector 7",
  current_aqi: 245.0,
  factors: [
    { name: "Traffic", icon: "🚗", percentage: 35.0, shap_value: 12.4 },
    { name: "Weather", icon: "🌦️", percentage: 30.0, shap_value: 10.1 },
    { name: "Industrial", icon: "🏭", percentage: 25.0, shap_value: 8.7 },
    { name: "Burning", icon: "🔥", percentage: 5.0, shap_value: 1.8 },
    { name: "Construction", icon: "🏗️", percentage: 5.0, shap_value: 1.5 },
  ],
  explanation: "AQI in Rohini is elevated primarily due to traffic congestion (35%) and unfavorable wind conditions (30%).",
  forecast_trend: "worsening"
};

export const mockEnforce = {
  city: "delhi",
  total_tickets: 15,
  high_urgency_count: 3,
  wards_affected: 12,
  tickets: [
    { ticket_id: "TCK-001", ward_id: "anand_vihar", ward_name: "Anand Vihar", urgency: "HIGH", forecast_aqi: 410, primary_cause: "Construction", primary_cause_icon: "🏗️", primary_cause_percentage: 40.0, recommended_action: "Suspend construction permits for 48 hours", estimated_aqi_reduction: "15-20%", affected_population: 45000, schools_in_zone: 2, hospitals_in_zone: 1, generated_at: "2026-07-03T10:00:00Z" },
    { ticket_id: "TCK-002", ward_id: "wazirpur", ward_name: "Wazirpur", urgency: "HIGH", forecast_aqi: 370, primary_cause: "Industrial", primary_cause_icon: "🏭", primary_cause_percentage: 52.0, recommended_action: "Issue notice to industrial units, enforce emission limits", estimated_aqi_reduction: "20-25%", affected_population: 38000, schools_in_zone: 1, hospitals_in_zone: 0, generated_at: "2026-07-03T10:00:00Z" },
    { ticket_id: "TCK-003", ward_id: "rohini_sector_7", ward_name: "Rohini Sector 7", urgency: "HIGH", forecast_aqi: 350, primary_cause: "Traffic", primary_cause_icon: "🚗", primary_cause_percentage: 35.0, recommended_action: "Implement odd-even vehicle restriction for 24 hours", estimated_aqi_reduction: "10-15%", affected_population: 62000, schools_in_zone: 4, hospitals_in_zone: 2, generated_at: "2026-07-03T10:00:00Z" },
    { ticket_id: "TCK-004", ward_id: "shahdara", ward_name: "Shahdara", urgency: "MEDIUM", forecast_aqi: 310, primary_cause: "Burning", primary_cause_icon: "🔥", primary_cause_percentage: 35.0, recommended_action: "Deploy anti-burning patrol teams", estimated_aqi_reduction: "8-12%", affected_population: 28000, schools_in_zone: 3, hospitals_in_zone: 1, generated_at: "2026-07-03T10:00:00Z" },
    { ticket_id: "TCK-005", ward_id: "dwarka", ward_name: "Dwarka", urgency: "MEDIUM", forecast_aqi: 295, primary_cause: "Traffic", primary_cause_icon: "🚗", primary_cause_percentage: 48.0, recommended_action: "Deploy traffic management at key intersections", estimated_aqi_reduction: "10-12%", affected_population: 52000, schools_in_zone: 5, hospitals_in_zone: 1, generated_at: "2026-07-03T10:00:00Z" },
  ]
};

export const mockVulnerable = {
  city: "delhi",
  total_locations: 6,
  locations: [
    { name: "AIIMS Delhi", type: "hospital", lat: 28.5672, lon: 77.2100, ward_id: "ansari_nagar", ward_name: "Ansari Nagar" },
    { name: "Safdarjung Hospital", type: "hospital", lat: 28.5687, lon: 77.2063, ward_id: "safdarjung", ward_name: "Safdarjung" },
    { name: "Delhi Public School, Rohini", type: "school", lat: 28.7325, lon: 77.1142, ward_id: "rohini_sector_7", ward_name: "Rohini Sector 7" },
    { name: "Kendriya Vidyalaya, Dwarka", type: "school", lat: 28.5945, lon: 77.0478, ward_id: "dwarka", ward_name: "Dwarka" },
    { name: "St. Columba's School", type: "school", lat: 28.6274, lon: 77.2124, ward_id: "connaught_place", ward_name: "Connaught Place" },
    { name: "RML Hospital", type: "hospital", lat: 28.6368, lon: 77.2006, ward_id: "connaught_place", ward_name: "Connaught Place" },
  ]
};

export const mockWhatIf = {
  ward_id: "rohini_sector_7",
  ward_name: "Rohini Sector 7",
  intervention: "pause_construction",
  duration_hours: 48,
  current_forecast: 350.0,
  with_intervention: 297.0,
  reduction: 53.0,
  reduction_percentage: 15.1
};