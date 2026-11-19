# Manual test walk-through (about 20 minutes)

Start the backend with `run_backend.bat`, the reminders window, and `npm run dev`. Use seed_demo.py data or your own.
Keep `PAYMENT_PROVIDER=mock` and `SMS_PROVIDER=console` while testing.

| # | Do this | You should see |
|---|---|---|
| 1 | Register a hospital at /hospital-register | Message that approval is needed. The hospital is NOT on /hospitals |
| 2 | Try to log in as that hospital admin | Login refused (not approved) |
| 3 | Log in as `admin`, open Dashboard then Approvals, approve it | Hospital now on /hospitals, approval e-mail sent |
| 4 | Log in as the hospital admin: add a department, a doctor (with a fee), and a schedule for today | Doctor shows "Visible to patients" |
| 5 | Add a receptionist (hospital admin only) and log in as them | Lands on the Reception desk |
| 6 | As a patient book a slot for today (a time still in the future) | Token + QR ticket, confirmation e-mail, SMS text in the backend window |
| 7 | Try booking the same slot as a second patient | "already booked" |
| 8 | Patient: Pay on My Appointments (demo confirm) | Status Paid, receipt e-mail |
| 9 | Reception: scan the QR (or use the check-in button) | Checked in; scanning again says "already used" |
| 10 | Reception: add a walk-in patient | Next token number, appears in the list |
| 11 | Open the lobby display (button on the Reception desk) in a second tab | Tokens appear and update by themselves |
| 12 | Doctor: Call next patient | Lobby display and the patient's page update; patient hears/sees the alert when 2 or fewer are ahead |
| 13 | Doctor: Write prescription, save, Download PDF | PDF file downloads; patient gets an e-mail and sees it on My Appointments |
| 14 | Doctor: Complete consultation | Moves to Recently completed |
| 15 | Reception: record cash for an unpaid walk-in | Payment column says Paid |
| 16 | Patient: cancel a paid future booking | Refund due badge + cancellation e-mail |
| 17 | Admin Dashboard: change the range, run the report, download CSV | Numbers match what you did; CSV opens in Excel |
| 18 | Admin Users: deactivate the patient | That patient is signed out and cannot log in; Reactivate restores access |
| 19 | Admin Users: delete a user with no history | Removed. Deleting a user with appointments is refused |
| 20 | Stop `npm run dev`'s backend window with the WebSocket and watch a queue page | It keeps refreshing every 5 seconds |
