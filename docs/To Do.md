## To Do

### ~~Getting an 'unsuffecient data' text at the top of the page~~ ✅
Root cause: `data/live_api.json` didn't exist on fresh start. Fixed by auto-fetching live data on startup if the cache file is missing. Also changed the message from "Insufficient data" to "Waiting for data — click Refresh", and auto-triggers a data refresh from the frontend.

### ~~dashboard just says loading against everything, eg porfolio loading, trading engine-loading~~ ✅
Changed default card text from "Loading..." to sensible defaults ("$0.00 / No open positions", "Connecting...") so the dashboard looks correct immediately. The overview cards update once data loads rather than sitting on "Loading" forever.