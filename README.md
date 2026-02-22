# DABN23 Project — Dynamic Travel Intelligence System

## Overview

This project implements a dynamic travel planning system that combines structured API-based data retrieval with live web scraping to generate curated city recommendations and real-time crowdedness insights.

For any given city, the system:

* Retrieves the **Top 10 must-see attractions** via Google Maps API
* Retrieves the **Top 10 activities** via TripAdvisor API
* Stores structured results in a persistent SQL database
* Uses Selenium to extract **real-time busyness ("Popular Times") data** from Google Maps

The project demonstrates the integration of APIs, database persistence, interactive notebooks, and live browser automation into a cohesive data pipeline.

---

## Architecture

The system is divided into three logical layers:

### 1️⃣ Static Data Ingestion (APIs)

* **Google Maps API**
  Retrieves attraction metadata (name, address, rating, categories, etc.)

* **TripAdvisor API**
  Retrieves activity data (name, rating, activity type, etc.)

All retrieved data is stored in a structured SQLite database for long-term persistence.

---

### 2️⃣ Persistent Storage Layer

* SQLite database shared across components
* Separate tables for item summaries and city-level Top-10 mappings
* Designed for dynamic extension (new cities can be added on demand)

---

### 3️⃣ Live Data Retrieval (Selenium)

* Automated Google Maps interaction via Selenium
* Extraction of full-day hourly crowdedness data
* Real-time snapshot of current busyness
* Data stored in structured dictionary format

This component represents the core hands-on Selenium implementation developed during the course.

---

## Project Structure

```
dabn23/
│
├── notebooks/
│   └── city_explorer.ipynb
│
├── src/
│   ├── cache.py
│   ├── config.py
│   ├── db.py
│   ├── google_places.py
│   ├── pipelines.py
│   ├── routing.py
│   ├── selenium_driver.py
│   ├── selenium_peak_hours.py
│   ├── tripadvisor.py
│   └── ui.py
│
└── README.md
```

---

## How to Run

### 1️⃣ Requirements

You need:

* Python 3.10+
* Google Maps API key
* TripAdvisor API key
* Chrome browser installed
* A VPN connected to an English-speaking country (recommended)

Install dependencies:

```bash
pip install requests pandas ipywidgets selenium
```

---

### 2️⃣ Configure Environment Variables

Set the following system variables:

* `GOOGLE_API_KEY`
* `TA_API_KEY`
* `DB_PATH` (path to SQLite database)

These values are loaded via `config.py`.

---

### 3️⃣ Run the Notebook

1. Open `notebooks/city_explorer.ipynb`
2. Use the interactive city widget
3. Retrieve Top 10 attractions and activities
4. Execute the Selenium scraping cells to collect live crowdedness data

---

## Key Design Decisions

### VPN & Language Consistency

Google Maps dynamically changes its DOM structure depending on:

* Geographic location
* Language
* Consent flows

For scraping stability, a VPN connected to an English-speaking country is recommended.

---

### Controlled Scraping Speed

The Selenium implementation deliberately includes pauses to:

* Avoid triggering anti-bot mechanisms
* Improve scraping stability
* Maintain reproducibility in a course setting

---

### Modular Design

Selenium logic was moved from the notebook into dedicated `.py` files to:

* Improve readability
* Improve maintainability
* Preserve notebook clarity
* Demonstrate architectural separation

---

## Limitations

* Scraping depends on Google Maps DOM stability
* Peak-hour data is only available for Google-sourced attractions
* Scraping speed is intentionally conservative
* Database updates are not automated (manual refresh required)

---

## Learning Outcomes

This project demonstrates:

* API integration (Google & TripAdvisor)
* SQL database design
* Interactive notebook UI design
* Selenium-based browser automation
* Handling of geo-sensitive web rendering
* End-to-end data pipeline architecture

---

## Documentation Disclaimer

This README was fully generated using AI (ChatGPT).
It is intended solely to document and explain the project structure, architecture, and usage.
All technical implementation — including APIs, database design, and Selenium scraping — was developed independently as part of the DABN23 course.