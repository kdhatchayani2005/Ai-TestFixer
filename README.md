# AI TestFixer - Self-Healing Test Automation Framework

An Intelligent Agent-Based Self-Healing Framework for Selenium Test Automation.

## 1. Project Overview
AI TestFixer is a production-style test automation framework that dynamically detects, analyzes, and heals broken Selenium locators in real-time. By utilizing local machine learning models through Ollama (Llama3) alongside custom heuristics and DOM similarity scoring, it acts as a self-healing layer. This ensures that minor frontend updates (e.g. ID shifts, class changes) do not disrupt continuous integration pipelines.

## 2. Architecture
The diagram below details the end-to-end self-healing orchestration flow when an exception is detected during test execution:

```
[Start Test Run] 
       │
       ▼
[Find Username/Password] (Success)
       │
       ▼
[Find Login Button] ──(Succeeds)──► [Direct PASS] ──► [Log Run (LogAgent)] ──► [Finish]
       │
   (Fails: NoSuchElement/Timeout/Stale/NotInteractable)
       │
       ▼
[FailureDetector] ──► [ScreenshotAgent] ──► [LogAgent] (Log Fail) ──► [DOMAnalyzer]
                                                                          │
                                                                          ▼
┌───────────────────[RetryIntelligence (Retry Loop max=3)]◄───────────────┘
│
├─► [Check Learned Fixes] ──(Found)──► [SelfHealer] ──► [Validator] ──(Pass)──► [PASS (Healed)] ──┐
│                                                                                                │
└─► [Check Learned Fixes] ──(None)──► [AIAgent (Ollama)] ──► [SelfHealer]                        │
                                                                  │                              │
                                                                  ▼                              │
                                                             [Validator]                         │
                                                                  │                              │
                                                               (Pass)                            │
                                                                  │                              │
                                                                  ▼                              │
                                                           [LearningAgent] ──► [PASS (Healed)] ──┤
                                                                                                 │
                                                                                                 ▼
                                                                                   [PerformanceMonitor.stop()]
                                                                                                 │
                                                                                                 ▼
                                                                                     [AlertNotification]
                                                                                                 │
                                                                                                 ▼
                                                                                            [AutoCleanup]
                                                                                                 │
                                                                                                 ▼
                                                                                              [Finish]
```

## 3. Folder Structure
The framework is structured as follows:

```
AI-TestFixer/
├── agents/
│   ├── failure_detector.py
│   ├── screenshot_agent.py
│   ├── log_agent.py
│   ├── dom_analyzer.py
│   ├── ai_agent.py
│   ├── self_healer.py
│   ├── validator.py
│   ├── learning_agent.py
│   ├── performance_monitor.py
│   ├── retry_intelligence.py
│   ├── alert_notification.py
│   └── auto_cleanup.py
├── database/
│   ├── db_manager.py
│   └── testfixer.db         (SQLite DB, created dynamically)
├── dashboard/
│   └── app.py
├── tests/
│   └── login_test.py
├── website/
│   └── login.html
├── screenshots/             (PNG failures, created dynamically)
├── logs/
│   ├── archive/             (Archived log files, created dynamically)
│   └── login_test.log       (Runtime logs, created dynamically)
├── reports/
│   └── test_report.pdf      (PDF report, created dynamically)
├── prompts_used.md
├── requirements.txt
└── README.md
```

## 4. Technology Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | `3.11+` | Core execution language |
| **Streamlit** | `1.32.0` | Multi-page telemetry dashboard |
| **Selenium** | `4.18.1` | Web automation and interactions |
| **Ollama REST API**| `11434` | Interface to local Llama3 LLM |
| **SQLite3** | `Built-in` | Database storage engine |
| **BeautifulSoup4**| `4.12.3` | HTML parser for DOM analysis |
| **Pandas** | `2.2.1` | Telemetry data processing |
| **Plotly** | `5.20.0` | Rich analytics charting |
| **ReportLab** | `4.1.0` | PDF generation |

## 5. Agent Descriptions
1. **FailureDetector**: Filters raw Selenium errors and identifies if the exception type is healable (`NoSuchElementException`, `TimeoutException`, `StaleElementReferenceException`, `ElementNotInteractableException`). It inserts a record of the failure into the SQLite database.
2. **ScreenshotAgent**: Saves the visual browser state at the time of failure using driver screenshot methods, generating sanitised, Windows-safe paths.
3. **LogAgent**: Appends structured, parsing-friendly log entries to local log files and logs run entries in the test history database.
4. **DOMAnalyzer**: Inspects the failing page source, comparing all tags with the failed locator using a sequence matcher to rank elements by similarity.
5. **AIAgent**: Packages the DOM context, failed locator, and page info, and makes a POST call to a local Ollama endpoint requesting a structured JSON recommendation.
6. **SelfHealer**: Executes the driver element resolution at runtime using the newly recommended locators.
7. **Validator**: Interacts with the recovered element (clicks/types) to confirm it is fully functional, reporting the execution speed back to the system.
8. **LearningAgent**: Manages framework database memory by registering new resolved locators or incrementing usage counters on recurring fixes.
9. **PerformanceMonitor**: Tracks timing parameters, calculates rolling historical execution speeds, and flags slow executions.
10. **RetryIntelligence**: Orchestrates wait backoffs and directs recovery flows, bypassing AI suggestions if a fix is already known.
11. **AlertNotification**: Evaluates hourly error counts and alerts engineering via SMTP SSL if error frequencies exceed configured thresholds.
12. **AutoCleanup**: Monitors test run counts to clear stale screenshots (>7 days), archive log files (>30 days), and de-duplicate the database.

## 6. Database Schema
SQLite database `database/testfixer.db` contains the following tables:

*   **failures**:
    `id` (INTEGER PRIMARY KEY), `locator` (TEXT), `error` (TEXT), `timestamp` (TEXT), `screenshot_path` (TEXT), `ai_suggestion` (TEXT)
*   **learned_fixes**:
    `id` (INTEGER PRIMARY KEY), `old_locator` (TEXT), `new_locator` (TEXT), `confidence` (REAL), `usage_count` (INTEGER)
*   **test_history**:
    `id` (INTEGER PRIMARY KEY), `test_name` (TEXT), `status` (TEXT), `execution_time` (REAL), `healed` (INTEGER)
*   **performance**:
    `id` (INTEGER PRIMARY KEY), `test_name` (TEXT), `execution_time` (REAL), `avg_time` (REAL), `status` (TEXT), `timestamp` (TEXT)
*   **alerts**:
    `id` (INTEGER PRIMARY KEY), `alert_type` (TEXT), `message` (TEXT), `timestamp` (TEXT), `sent_status` (INTEGER)
*   **retry_log**:
    `id` (INTEGER PRIMARY KEY), `test_name` (TEXT), `retry_count` (INTEGER), `final_status` (TEXT), `timestamp` (TEXT)
*   **cleanup_counter**:
    `counter_val` (INTEGER)

## 7. Installation Steps
1. **Pull and Launch Ollama**:
   Install Ollama on your machine and run:
   ```bash
   ollama run llama3
   ```
   Ensure the service is listening at `http://localhost:11434`.
2. **Install Chrome Browser**:
   Ensure Google Chrome is installed on the execution machine.
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 8. How to Run the Demo
*   **Run a Successful Test (Direct Pass)**:
    ```bash
    python tests/login_test.py --locator loginBtn
    ```
*   **Run a Broken Test (Triggers Self-Healing)**:
    ```bash
    python tests/login_test.py --locator loginButton
    ```
*   **Launch Streamlit Dashboard**:
    ```bash
    streamlit run dashboard/app.py
    ```

## 9. Demonstration Scenario
1. We execute `login_test.py` with `--locator loginButton`.
2. The Selenium driver loads `website/login.html` (which defines the button ID as `loginBtn`).
3. Selenium fails to locate `loginButton` and raises `NoSuchElementException`.
4. `FailureDetector` catches it, `DOMAnalyzer` finds `loginBtn` with a similarity score of 0.82.
5. `RetryIntelligence` queries `AIAgent`. Ollama receives the context and recommends replacing `loginButton` with `loginBtn` with high confidence.
6. `SelfHealer` and `Validator` click `loginBtn` and successfully submit the form.
7. `LearningAgent` saves the mapping. Subsequent runs of `--locator loginButton` bypass the AI and immediately heal the test using the database!

## 10. Compliance Checklist
*   **AI-Generated Elements**: All suggested locators are generated dynamically by Ollama.
*   **No Dummy/Mock Telemetry**: Every KPI metric and graph is built on live database rows.
*   **Agent Loop Orchestration**: Complete execution tracking from failure trap to post-heal validation.

## 11. Future Enhancements
*   Integrate healing for XPath structure adjustments.
*   Implement self-healing rules for visual regression failures.
*   Add multi-browser testing grids support.
