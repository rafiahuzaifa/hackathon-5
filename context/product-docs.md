# TaskFlow Pro — Product Documentation & FAQ

## ACCOUNT SETUP

### Q: How do I create a TaskFlow Pro account?
A: Visit app.techcorp.pk and click "Start Free Trial." Enter your work email, choose a password (min 8 chars, 1 uppercase, 1 number), and verify your email. Your 14-day free trial begins immediately with no credit card required.

### Q: Can I invite team members?
A: Yes. Go to Settings → Team Members → Invite. Enter their email addresses (comma-separated for bulk invite). They'll receive an invitation link valid for 7 days. You can assign roles: Admin, Manager, Member, or Viewer.

### Q: What are the different user roles?
A:
- **Admin**: Full access — billing, settings, all projects, user management
- **Manager**: Create/edit projects, assign tasks, view reports
- **Member**: Create/complete tasks, comment, track time
- **Viewer**: Read-only access to assigned projects

### Q: How do I set up my company workspace?
A: After signup, go to Settings → Workspace. Add your company name, logo (PNG/JPG, max 2MB), timezone, and date format. These settings apply to all team members.

---

## LOGIN & AUTHENTICATION

### Q: I forgot my password. How do I reset it?
A: On the login page, click "Forgot Password." Enter your registered email. You'll receive a reset link within 2 minutes. The link expires after 1 hour. If you don't receive it, check spam or contact support.

### Q: Can I use Single Sign-On (SSO)?
A: Yes, SSO is available on Business and Enterprise plans via Google Workspace, Microsoft Azure AD, and Okta. Go to Settings → Security → SSO to configure. Contact your IT admin for SAML configuration details.

### Q: Why is my account locked?
A: Accounts are locked after 5 failed login attempts for 30 minutes as a security measure. Wait 30 minutes and try again, or use the password reset flow. If you believe your account was compromised, contact support immediately.

### Q: How do I enable two-factor authentication (2FA)?
A: Go to Profile → Security → Enable 2FA. We support authenticator apps (Google Authenticator, Authy) and SMS. We strongly recommend authenticator apps for better security.

---

## TASK MANAGEMENT

### Q: How do I create a task?
A: Click the "+" button in any project list, or press "T" as a keyboard shortcut. Add a title, then optionally set: assignee, due date, priority (Low/Medium/High/Urgent), description, tags, and attachments. Tasks can be created via our mobile app or API too.

### Q: How do task dependencies work?
A: Open a task, click "Dependencies," and select "Blocks" or "Blocked by." Dependent tasks show a warning icon when their blocking task is incomplete. On Gantt view, dependencies appear as arrows between tasks.

### Q: Can I set recurring tasks?
A: Yes. In task settings, click "Recurrence." Choose Daily, Weekly, Monthly, or Custom (e.g., every 2nd Tuesday). The next occurrence is auto-created when you complete the current one.

### Q: How do I bulk-edit tasks?
A: In List view, check the checkbox next to multiple tasks. A bulk action bar appears at the bottom. You can bulk: assign, set due dates, change priority, add tags, move to another list, or delete.

### Q: What are Custom Fields?
A: Custom Fields let you add project-specific data to tasks: text, number, date, dropdown, checkbox, or URL fields. Go to Project Settings → Custom Fields to create them. Available on Pro plan and above.

---

## PROJECTS & BOARDS

### Q: What's the difference between Lists, Boards, and Gantt views?
A: All three views show the same tasks — just differently:
- **List**: Classic to-do format, best for large task volumes
- **Board (Kanban)**: Drag-and-drop cards through columns (To Do → In Progress → Done)
- **Gantt**: Timeline view showing task durations and dependencies, best for project planning

### Q: How do I archive a completed project?
A: Go to Project Settings → Archive Project. Archived projects are hidden from the main sidebar but remain fully accessible via the Archive section. All data is preserved.

### Q: Can I use templates for new projects?
A: Yes. When creating a project, choose "From Template." We offer 20+ built-in templates (Software Sprint, Marketing Campaign, Onboarding Checklist, etc.). You can also save any project as a custom template.

---

## BILLING & SUBSCRIPTIONS

### Q: What plans are available?
A: We offer Starter, Pro, Business, and Enterprise plans. For current pricing and plan comparisons, please contact our sales team at sales@techcorp.pk. We do not disclose pricing in support channels.

### Q: How do I upgrade or downgrade my plan?
A: For plan changes, please contact our sales team at sales@techcorp.pk or call +92-21-1234567 during business hours. They will guide you through the process and ensure a smooth transition.

### Q: I have a billing question or dispute.
A: All billing inquiries must go through our sales and accounts team at billing@techcorp.pk. Please include your account email and invoice number. Our team responds within 1 business day.

---

## API & INTEGRATIONS

### Q: Does TaskFlow Pro have an API?
A: Yes. We offer a REST API with OAuth2 authentication. API documentation is available at docs.techcorp.pk/api. Rate limits: 1,000 requests/hour on Pro, 10,000 on Business, unlimited on Enterprise.

### Q: How do I connect Slack?
A: Go to Settings → Integrations → Slack → Connect. Authorize the TaskFlow app in Slack. Then configure which channels receive notifications (task assignments, due dates, comments). Each project can send to a different Slack channel.

### Q: How do I import data from Jira?
A: Go to Settings → Import → Jira. Export your Jira project as XML (from Jira: Projects → Export). Upload the XML file. We'll map Jira issues to TaskFlow tasks, preserving comments, attachments, and history. Large imports (>10,000 issues) may take up to 30 minutes.

### Q: Is there a Zapier integration?
A: Yes. Search "TaskFlow Pro" in Zapier. We support triggers (task created, task completed, comment added) and actions (create task, update task). Available on Pro plan and above.

---

## MOBILE APP

### Q: Where can I download the mobile app?
A: TaskFlow Pro is available on iOS (App Store) and Android (Google Play Store). Search "TaskFlow Pro" or scan the QR code at techcorp.pk/mobile. Requires iOS 14+ or Android 8+.

### Q: Does the app work offline?
A: Yes. You can view and edit tasks offline. Changes sync automatically when you reconnect. Offline mode supports task creation, editing, status changes, and comments. File uploads require connectivity.

### Q: Why is the app not syncing?
A: First, check your internet connection. Then try: Pull-to-refresh in the app → Log out and log back in → Uninstall and reinstall. If the issue persists, go to Settings → Diagnostics → Send Report so our team can investigate.

---

## REPORTING & EXPORTS

### Q: How do I export my project data?
A: Go to Project → Export. Choose format: CSV (tasks), Excel (tasks + custom fields), or PDF (Gantt chart). For full workspace export (all projects, members, history), go to Settings → Export Workspace. Enterprise accounts can schedule automated exports.

### Q: How does the burndown chart work?
A: The burndown chart tracks remaining work vs. time in a sprint. It plots ideal burn rate vs. actual. Access it in Reports → Sprint Reports. Requires tasks to have story points (custom field) and sprint dates defined.

---

## NOTIFICATIONS

### Q: How do I control email notifications?
A: Go to Profile → Notifications. Toggle notifications for: task assignments, due date reminders, comments @mentioning you, task completions, and project updates. You can also set a "notification digest" to receive one daily email instead of individual ones.

### Q: How do I set up due date reminders?
A: In task settings, click the bell icon next to the due date. Set reminders: 1 hour, 1 day, 3 days, or custom before due date. Reminders go to your registered email and mobile push notifications.

---

## COMMON ERRORS & FIXES

### Q: I'm getting a "401 Unauthorized" error in the API.
A: Your access token has expired. Tokens expire after 1 hour. Use your refresh token to get a new access token, or re-authenticate. Check that you're including the token in the Authorization header as: `Bearer YOUR_TOKEN`.

### Q: Tasks are not appearing in my Gantt chart.
A: Gantt chart requires tasks to have both a start date and due date set. Tasks with only a due date appear as milestones (diamond shape). Ensure dates are set on all tasks you want to see in Gantt view.

### Q: The app is running slow.
A: Try these steps:
1. Clear browser cache (Ctrl+Shift+Delete)
2. Disable browser extensions temporarily
3. Switch to a different browser
4. Check your internet speed (minimum 5 Mbps recommended)
5. If issues persist, check techcorp.pk/status for system incidents

### Q: I accidentally deleted tasks. Can I recover them?
A: Yes! Deleted tasks go to the Trash (Project → Trash or Workspace → Trash). Items remain for 30 days. Click "Restore" to recover. After 30 days, deletion is permanent. For data older than 30 days, contact support — we may be able to help for Enterprise accounts.

### Q: Team members aren't receiving invitation emails.
A: Check: (1) Email was entered correctly, (2) Their email server isn't blocking techcorp.pk domain, (3) Check their spam folder. You can resend invitations from Settings → Team → Pending Invitations → Resend. If still failing after 24 hours, contact support with the team member's email.
