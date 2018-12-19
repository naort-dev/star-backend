# Load tests 
## Installing locust.io
For installation refer to the documentation [https://docs.locust.io/en/stable/]()

## Debug tests
Intellij Python debugger setup:
* Build, Execution, Deployment > Python Debugger 
  * Check "Gevent compatible" option

Run locustfile.py under debugger, it will run in single user mode 
and you will be able to step thru the code.

## Run tests
Run tests in UI mode

```
(venv) ~/starsona/backend/tests$ locust --host=https://app.staging.starsona.com
[2018-12-18 20:47:54,993] local/INFO/locust.main: Starting web monitor at *:8089
[2018-12-18 20:47:54,994] local/INFO/locust.main: Starting Locust 0.9.0
[2018-12-18 20:48:37,049] local/INFO/locust.runners: Hatching and swarming 50 clients at the rate 1 clients/s...
[2018-12-18 20:49:27,184] local/INFO/locust.runners: All locusts hatched: WebsiteUser: 50
```

* Open web UI at [http://localhost:8089]()
* Enter how many users and how fast to hatch

## Running tests in batch mode

TBD 