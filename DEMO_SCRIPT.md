# ⏱️ Smart Payment Advisor — 2-Minute Live Presentation Demo Script

This presentation script guides you through demonstrating the Smart Payment Advisor platform to judges or evaluators in 2 minutes.

---

### Step 1: Normal Checkout State & Smart Recommender (0:00 - 0:30)
- **Action**: Open `http://localhost:5173`. Click **Checkout Portal**, enter student/customer details (e.g. ₹18,000), and click **Pay Now**.
- **What to say**:
  > *"When a customer arrives at checkout, Smart Payment Advisor queries our real-time AI engine. Notice how payment options are ranked not statically, but by live success probability, transaction fees, and confidence intervals ($80.7\% \pm 8.5\%$). The top option is highlighted as 'Recommended' because it offers the highest success probability at zero extra fee."*

---

### Step 2: Simulate Bank Outage (0:30 - 0:50)
- **Action**: Click the **Simulator** tab in the top header. Select **Electricity Bill Portal** (or active merchant) and target **Net Banking - HDFC**. Set failure count to 15 transactions and click **Trigger Bank Outage & Failure Spike**.
- **What to say**:
  > *"Payment downtime happens unexpectedly. In our Simulator, we inject 15 artificial failure records into HDFC Net Banking to simulate a real-time gateway outage."*

---

### Step 3: Instant Live Re-Ranking Demonstration (0:50 - 1:15)
- **Action**: Look at the **Live Impact Preview** section right below the simulator control.
- **What to say**:
  > *"Watch what happens instantly in the Live Impact Preview without touching or refreshing the page. Thanks to database-level window aggregations and exponential recency weighting ($w = e^{-0.0277t}$), HDFC Net Banking plummets to 0% success rate and is flagged with 'Critical downtime detected (61.5 pts below baseline)'. The system automatically demotes it to the bottom and promotes SBI Debit Card / UPI to top rank."*

---

### Step 4: Real-Time Analytics & Fee Savings (1:15 - 1:40)
- **Action**: Click the **Analytics** tab in the top header.
- **What to say**:
  > *"Merchants get complete visibility in our Analytics Dashboard. We monitor global completion rates, pinpoint the top failing gateway in real time, and calculate cumulative fee savings achieved by steering transactions away from failing high-cost options."*

---

### Step 5: Execute Test Payment & Razorpay Flow (1:40 - 2:00)
- **Action**: Switch back to **Checkout Portal**, select the top recommended method, click **Proceed to Pay**, and show the Razorpay payment flow / simulation mode modal authentication.
- **What to say**:
  > *"Finally, when the user clicks 'Proceed to Pay', the order is created via Razorpay's Python SDK, authenticated via payment signature verification, and logged into our SQLite database. Smart Payment Advisor turns payment routing from a static guesswork process into a real-time reliability engine."*
