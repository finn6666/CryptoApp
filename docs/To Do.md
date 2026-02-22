## To Do

### ~~Dashboard data takes ~15 mins to appear~~ ✅
Three issues combined: (1) auto-refresh only reloaded market conditions, not overview cards/favorites — fixed to reload the full dashboard. (2) `/api/refresh` blocked on fetching individual missing symbols — moved to background thread. (3) No fast retry — added 10-second retry loop for the first 2 minutes after page load. Data now appears within seconds of becoming available.

### 