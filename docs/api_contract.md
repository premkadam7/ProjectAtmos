# Atmos API Contract

This document outlines the API endpoints, request parameters, and response structures that the backend will provide. **Frontend dev: use these exact shapes to build your UI.**

## Base URL
`http://localhost:8000`

---

## 1. Health Check
Check if the API is running.

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2026-07-01T23:57:00.000000"
}
```

---

## 2. City Forecast Overview
Get the 72h forecast summary for all wards in a city (used for the dashboard and map coloring).

**Endpoint:** `GET /api/forecast/{city}` (e.g. `/api/forecast/delhi`)

**Response:**
```json
{
  "city": "delhi",
  "generated_at": "2026-07-01T23:00:00Z",
  "total_wards": 250,
  "city_avg_aqi": 215.4,
  "worst_ward": "rohini_sector_7",
  "best_ward": "vasant_kunj",
  "wards": [
    {
      "ward_id": "rohini_sector_7",
      "ward_name": "Rohini Sector 7",
      "lat": 28.72,
      "lon": 77.10,
      "current_aqi": 245.0,
      "forecast_aqi_24h": 285.5,
      "forecast_aqi_48h": 270.0,
      "forecast_aqi_72h": 210.0,
      "trend": "worsening",
      "cigarette_equivalent": 5.2
    }
  ]
}
```

---

## 3. Ward Forecast Detail
Get detailed hourly forecast and uncertainty bands for a single ward.

**Endpoint:** `GET /api/forecast/{city}/{ward_id}` (e.g. `/api/forecast/delhi/rohini_sector_7`)

**Response:**
```json
{
  "ward_id": "rohini_sector_7",
  "ward_name": "Rohini Sector 7",
  "city": "delhi",
  "generated_at": "2026-07-01T23:00:00Z",
  "current_aqi": 245.0,
  "current_pm25": 115.5,
  "cigarette_equivalent": 5.2,
  "hourly": [
    {
      "timestamp": "2026-07-02T00:00:00Z",
      "aqi": 250.0,
      "pm25": 120.0,
      "pm10": 200.0,
      "aqi_low": 235.0,
      "aqi_high": 270.0
    }
  ]
}
```

---

## 4. SHAP Blame Score
Get the attribution of pollution sources for a specific ward.

**Endpoint:** `GET /api/blame/{city}/{ward_id}`

**Response:**
```json
{
  "ward_id": "rohini_sector_7",
  "ward_name": "Rohini Sector 7",
  "current_aqi": 245.0,
  "factors": [
    { "name": "Traffic", "icon": "🚗", "percentage": 35.0, "shap_value": 12.4 },
    { "name": "Weather", "icon": "🌦️", "percentage": 30.0, "shap_value": 10.1 },
    { "name": "Industrial", "icon": "🏭", "percentage": 25.0, "shap_value": 8.7 },
    { "name": "Burning", "icon": "🔥", "percentage": 5.0, "shap_value": 1.8 },
    { "name": "Construction", "icon": "🏗️", "percentage": 5.0, "shap_value": 1.5 }
  ],
  "explanation": "AQI in Rohini is elevated primarily due to traffic congestion (35%) and unfavorable wind conditions (30%).",
  "forecast_trend": "worsening"
}
```

---

## 5. Enforcement Tickets
Get a prioritized list of enforcement recommendations based on forecasts and blame scores.

**Endpoint:** `GET /api/enforce/{city}`

**Response:**
```json
{
  "city": "delhi",
  "total_tickets": 15,
  "high_urgency_count": 3,
  "wards_affected": 12,
  "tickets": [
    {
      "ticket_id": "TCK-001",
      "ward_id": "rohini_sector_7",
      "ward_name": "Rohini Sector 7",
      "urgency": "HIGH",
      "current_aqi": 285.5,
      "primary_cause": "Construction",
      "primary_cause_icon": "🏗️",
      "primary_cause_percentage": 40.0,
      "recommended_action": "Suspend construction permits for 48 hours",
      "estimated_aqi_reduction": "15-20%",
      "affected_population": 45000,
      "schools_in_zone": 2,
      "hospitals_in_zone": 1,
      "generated_at": "2026-07-01T23:00:00Z"
    }
  ]
}
```

---

## 6. Chat (RAG Assistant)
Interact with the Atmos Assistant.

**Endpoint:** `POST /api/chat`

**Request Body:**
```json
{
  "message": "Why is AQI spiking in Rohini?",
  "language": "en",
  "conversation_id": null
}
```

**Response (Non-streaming fallback):**
```json
{
  "response": "The AQI in Rohini is currently spiking to 245 due to a combination of high traffic congestion (contributing 35%) and unfavorable wind conditions trapping pollutants (30%). I recommend staying indoors.",
  "language": "en",
  "conversation_id": "conv_12345",
  "sources": ["Blame Score Data", "Forecast Data"]
}
```
*(Note: Real implementation will likely use Server-Sent Events (SSE) for streaming text, but this is the final JSON payload shape).*

---

## 7. Vulnerable Locations
Get hospitals, schools, and elderly care centers for vulnerability overlay on the map.

**Endpoint:** `GET /api/vulnerable/{city}`

**Response:**
```json
{
  "city": "delhi",
  "total_locations": 3,
  "locations": [
    {
      "name": "AIIMS Delhi",
      "type": "hospital",
      "lat": 28.5672,
      "lon": 77.2100,
      "ward_id": "ansari_nagar",
      "ward_name": "Ansari Nagar"
    },
    {
      "name": "Delhi Public School, Rohini",
      "type": "school",
      "lat": 28.7325,
      "lon": 77.1142,
      "ward_id": "rohini_sector_7",
      "ward_name": "Rohini Sector 7"
    }
  ]
}
```

---

## 8. What-If Simulator (Stretch Goal)
Simulate the impact of an intervention on a ward's AQI.

**Endpoint:** `POST /api/whatif`

**Request Body:**
```json
{
  "ward_id": "rohini_sector_7",
  "intervention": "pause_construction",
  "duration_hours": 48
}
```

**Response:**
```json
{
  "ward_id": "rohini_sector_7",
  "ward_name": "Rohini Sector 7",
  "intervention": "pause_construction",
  "duration_hours": 48,
  "current_forecast": 245.0,
  "with_intervention": 208.0,
  "reduction": 37.0,
  "reduction_percentage": 15.1
}
```
