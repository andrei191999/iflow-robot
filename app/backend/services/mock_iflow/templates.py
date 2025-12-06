import json

# Client-side simulation bot script
SIMULATION_BOT_SCRIPT = """
<script>
class SimulationBot {
    constructor() {
        const params = new URLSearchParams(window.location.search);
        this.autoRun = params.get('auto_run') === 'true';
        this.speed = params.get('speed') || 'normal';
        this.delays = {
            slow: 1000,
            normal: 500,
            fast: 100
        };
        this.delay = this.delays[this.speed] || 500;

        if (this.autoRun) {
            console.log('🤖 Simulation Bot Activated', { speed: this.speed, delay: this.delay });
            this.init();
        }
    }

    async wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async type(selector, text) {
        const el = document.querySelector(selector);
        if (!el) {
            console.error('Element not found:', selector);
            return;
        }

        el.focus();
        el.value = '';

        // Simulate typing
        for (let char of text) {
            el.value += char;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            await this.wait(50); // Typing speed
        }

        el.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('Typed:', text, 'into', selector);
        await this.wait(this.delay);
    }

    async click(selector) {
        const el = document.querySelector(selector);
        if (!el) {
            console.error('Element not found:', selector);
            return;
        }
        await this.clickElement(el);
    }

    async clickElement(el) {
        if (!el) return;

        // Visual feedback
        const originalBorder = el.style.border;
        el.style.border = '2px solid red';
        await this.wait(200);
        el.style.border = originalBorder;

        el.click();
        console.log('Clicked:', el);
        await this.wait(this.delay);
    }

    async init() {
        // Page-specific logic implemented by subclasses or conditional
        if (document.getElementById('td_reg_email')) {
            await this.runLogin();
        } else if (document.querySelector('.td-check-in-out-button')) {
            await this.runDashboard();
        }
    }

    async runLogin() {
        const params = new URLSearchParams(window.location.search);
        const username = params.get('username') || 'demo@example.com';
        const password = params.get('password') || 'demo123';

        await this.wait(1000);
        await this.type('#td_reg_email', username);
        await this.type('#td_reg_password', password);
        await this.click('button[type="submit"]');
    }

    async runDashboard() {
        const params = new URLSearchParams(window.location.search);
        const eventType = params.get('event_type') || 'checkIn';
        const checkinTime = params.get('checkin') || '09:00';
        const checkoutTime = params.get('checkout') || '17:00';
        const location = params.get('location') || 'telemunca';

        await this.wait(1000);

        // 1. Click Check In/Out button
        await this.click('.td-check-in-out-button');

        // 2. Wait for modal
        await this.wait(1000);

        // 3. Select location
        if (location) {
            console.log('Selecting location:', location);
            // Open dropdown
            await this.click('.td-select-single-button');
            await this.wait(500);

            // Find option case-insensitive
            const options = Array.from(document.querySelectorAll('.location-option'));
            const targetOption = options.find(opt =>
                opt.textContent.trim().toLowerCase() === location.toLowerCase()
            );

            if (targetOption) {
                await this.clickElement(targetOption);
            } else {
                console.warn('Location option not found:', location);
                // Close dropdown
                await this.click('.td-select-single-button');
            }
            await this.wait(500);
        }

        // 4. Type time
        if (eventType === 'checkIn') {
            await this.type('#td-ckeck-in-out-start-time-65', checkinTime);
        } else if (eventType === 'checkOut') {
            // Checkin time is pre-filled by template logic, type checkout time
            await this.type('#td-ckeck-in-out-end-time-65', checkoutTime);
        }

        // 5. Submit
        await this.click('.btn.modal-default-button');

        // 6. Show success and close
        await this.wait(2000);

        // Create a success overlay
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 255, 0, 0.3)';
        overlay.style.display = 'flex';
        overlay.style.justifyContent = 'center';
        overlay.style.alignItems = 'center';
        overlay.style.zIndex = '9999';

        const actionText = eventType === 'checkIn' ? 'CHECK IN COMPLETE' : 'CHECK OUT COMPLETE';
        overlay.innerHTML = `<h1 style="color: white; text-shadow: 2px 2px 4px #000; font-size: 4em;">${actionText}</h1>`;
        document.body.appendChild(overlay);

        await this.wait(3000);

        const nextUrl = params.get('next_url');
        if (nextUrl) {
            console.log('Redirecting to next event:', nextUrl);
            window.location.href = nextUrl;
        } else {
            window.close();
        }
    }
}
// Start the bot
window.addEventListener('load', () => {
    new SimulationBot();
});
</script>
"""

def get_login_page(error: str = "") -> str:
    """
    Generate login page HTML with exact selectors from real iFlow.

    Selectors used:
    - #td_reg_email (username input)
    - #td_reg_password (password input)
    - button[type="submit"] (login button)
    """
    error_display = "block" if error else "none"
    error_msg = error if error else "false"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mock iFlow - Login</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f8f9fa;
        }}
        .mock-banner {{
            background: #ff6b6b;
            color: white;
            text-align: center;
            padding: 10px;
            font-weight: bold;
        }}
        .td-login-company {{
            margin-top: 50px;
        }}
        .td-login-register-wrap {{
            max-width: 400px;
            margin: 0 auto;
        }}
        .td-login-register-form {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .td-login-register-title {{
            text-align: center;
            margin-bottom: 20px;
            color: #333;
        }}
        .form-header-welcome h4 {{
            text-align: center;
            color: #666;
            margin-bottom: 20px;
        }}
        .td-login-button {{
            margin-top: 15px;
        }}
        .td-company-message-wrap {{
            margin-top: 15px;
            font-size: 13px;
        }}
        .td-alert-blue {{
            background-color: #e7f3ff;
            border-color: #b3d9ff;
            color: #004085;
        }}
    </style>
</head>
<body>
    <div class="mock-banner">MOCK iFlow Server - Testing Environment</div>
    <div class="td-router-view td-is-not-logged-in" style="margin-top: 36px;">
        <div data-v-4d9462c7="" class="td-login-company">
            <div data-v-4d9462c7="" class="container">
                <div data-v-4d9462c7="" class="row">
                    <div data-v-4d9462c7="" class="col-md-4"></div>
                    <div data-v-4d9462c7="" class="col-md-4 td-login-register-wrap td-login-register-long-form">
                        <div data-v-4d9462c7="" class="td-login-register-form">
                            <h1 data-v-4d9462c7="" class="td-login-register-title">Login</h1>
                            <form data-v-4d9462c7="" method="POST" action="/mock-iflow/login">
                                <div data-v-4d9462c7="" class="alert alert-danger" style="display: {error_display};"><span
                                        data-v-4d9462c7="">{error_msg}</span></div>
                                <div data-v-4d9462c7="" class="form-header-welcome">
                                    <h4 data-v-4d9462c7="">Welcome to HRiFlow!</h4>
                                </div>
                                <div data-v-4d9462c7="">
                                    <div data-v-4d9462c7="" class="form-group"><label data-v-4d9462c7=""
                                            for="td_reg_email">E-mail address</label> <input data-v-4d9462c7=""
                                            id="td_reg_email" name="username" type="text" placeholder="E-mail" tabindex="1"
                                            pattern="^[^@\\s]+@[^@\\s]+$" required="required" class="form-control"></div>
                                    <div data-v-4d9462c7="" class="form-group td-password-group"><label data-v-4d9462c7=""
                                            for="td_reg_password">Password</label>
                                        <p data-v-4d9462c7="" class="td-forgot-password"><a data-v-4d9462c7=""
                                                href="#/recover/en_EN" class="" tabindex="4">Forgot your password?</a></p>
                                        <div data-v-4d9462c7="" class="td-form-icon"><input data-v-4d9462c7=""
                                                id="td_reg_password" name="password" placeholder="Password" tabindex="2"
                                                required="required" type="password" class="form-control td-password-input">
                                            <div data-v-4d9462c7="" class="input-group-append td-show-password-wrap"><span
                                                    data-v-4d9462c7="" class="input-group-text"><i data-v-4d9462c7=""
                                                        aria-hidden="true" class="fa fa-eye-slash"></i></span></div>
                                        </div>
                                    </div>
                                </div>
                                <div data-v-4d9462c7="" class="td-company-message-wrap alert td-alert-blue">
                                    <div data-v-4d9462c7="" class="td-company-message-body">
                                        <div data-v-4d9462c7="">Demo credentials: <strong>demo@example.com</strong> / <strong>demo123</strong></div>
                                    </div>
                                </div> <button data-v-4d9462c7="" type="submit" tabindex="3"
                                    class="td-login-button btn btn-default btn-block">
                                    Log in
                                    <!----></button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
{SIMULATION_BOT_SCRIPT}
</body>
</html>
"""


def get_dashboard_page(session_id: str, event_type: str = None, checkin_time: str = None, checkout_time: str = None, location: str = None, date: str = None) -> str:
    """
    Generate dashboard page HTML with check-in button and modal using REAL iFlow HTML.

    Args:
        session_id: User session identifier
        event_type: Type of event (checkIn or checkOut) - determines which time field to show
        checkin_time: Optional check-in time in HH:MM format (e.g., "09:00")
        checkout_time: Optional check-out time in HH:MM format (e.g., "17:00")

    CRITICAL SELECTORS (from real iFlow):
    - .td-check-in-out-button (check-in button that opens modal)
    - #td-ckeck-in-out-start-time-65 (Clock IN time field)
    - #td-ckeck-in-out-end-time-65 (Clock OUT time field)
    - .btn.modal-default-button (submit button with text "Add")
    """

    # Determine if we're doing check-in only, check-out only, or both
    is_checkin = event_type == "checkIn"
    is_checkout = event_type == "checkOut"
    show_both = not event_type  # If no event_type specified, show both fields
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mock iFlow - Dashboard</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f8f9fa;
            margin: 0;
            padding: 0;
        }}
        .mock-banner {{
            background: #ff6b6b;
            color: white;
            text-align: center;
            padding: 10px;
            font-weight: bold;
        }}
        .navbar {{
            background: #3f51b5;
            color: white;
            padding: 15px 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .td-check-in-out {{
            text-align: center;
            padding: 50px 20px;
        }}
        .td-check-in-out-button {{
            display: inline-block;
            padding: 20px 50px;
            background: #4caf50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 20px;
            font-weight: 600;
            cursor: pointer;
            border: none;
        }}
        .td-check-in-out-button:hover {{
            background: #45a049;
            color: white;
            text-decoration: none;
        }}

        /* Modal styles from real iFlow */
        .modal-mask {{
            position: fixed;
            z-index: 9998;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: none;
            transition: opacity 0.3s ease;
        }}
        .modal-mask.show {{
            display: table;
        }}
        .modal-wrapper {{
            display: table-cell;
            vertical-align: middle;
        }}
        .modal-container {{
            width: 600px;
            margin: 0px auto;
            padding: 20px 30px;
            background-color: #fff;
            border-radius: 2px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.33);
            transition: all 0.3s ease;
        }}
        .modal-header {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 20px;
            position: relative;
            padding-bottom: 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .modal-close {{
            position: absolute;
            top: 0;
            right: 0;
            cursor: pointer;
            font-size: 24px;
        }}
        .modal-body {{
            margin: 20px 0;
        }}
        .modal-footer {{
            text-align: right;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
        .modal-footer .btn {{
            margin-left: 10px;
        }}
        .modal-default-button {{
            background: #3f51b5;
            color: white;
            border: none;
            padding: 10px 30px;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
        }}
        .modal-default-button:hover {{
            background: #303f9f;
        }}
        .cancel-btn {{
            background: #f5f5f5;
            padding: 10px 30px;
            border-radius: 4px;
            cursor: pointer;
        }}
        .cancel-btn a {{
            color: #666;
            text-decoration: none;
        }}

        /* Form styles */
        .form-group {{
            margin-bottom: 15px;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #333;
        }}
        .form-control {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }}
        .td-user-required-field {{
            color: red;
            margin-left: 2px;
        }}

        /* Location dropdown */
        .td-select-single-outer-wrap {{
            position: relative;
        }}
        .td-select-single {{
            position: relative;
        }}
        .td-select-single-button {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .td-select-single-button:after {{
            content: '▼';
            font-size: 10px;
        }}
        .td-select-list {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            z-index: 1000;
            margin-top: 5px;
        }}
        .td-elements-list {{
            max-height: 200px;
            overflow-y: auto;
        }}
        .location-option {{
            padding: 10px 12px;
            cursor: pointer;
        }}
        .location-option:hover {{
            background: #f5f5f5;
        }}
        .td-date-input-wrap, .td-time-picker {{
            width: 100%;
        }}
        .alert-danger {{
            background: #fee;
            color: #c33;
            border: 1px solid #fcc;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <div class="mock-banner">MOCK iFlow Server - Session: {session_id}</div>
    <div class="navbar">
        <div class="container">
            <strong>HRiFlow</strong> - Time Tracking Dashboard
        </div>
    </div>

    <div id="app">
        <div class="td-router-view">
            <div class="container">
                <div class="col-md-12 td-fit-container">
                    <div class="td-check-in-out">
                        <a title="" class="td-check-in-out-button btn" onclick="openModal(); return false;">
                            Clock in
                        </a>
                        <div class="td-check-in-out-extra"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal HTML from real iFlow -->
    <div class="td-checkin-modal">
        <div class="modal-mask shepherd-target shepherd-modal-target shepherd-enabled" id="checkinModal">
            <div class="modal-wrapper">
                <div class="modal-container">
                    <span class="modal-close td-icon-modal-close" onclick="closeModal()" style="cursor: pointer;">&times;</span>
                    <div class="modal-header">
                        Clock in
                        <div class="td-header-info"><span class="glyphicon glyphicon-info-sign"></span>
                            <div class="td-header-info-text" style="display: none;"><span>Description:</span>Here you can
                                add Clock In and Clock Out events through which the time spent at work will be recorded
                            </div>
                        </div>
                    </div>
                    <div class="modal-body">
                        <div>
                            <form id="checkinForm">
                                <input type="hidden" name="session_id" value="{session_id}">
                                <div class="row">
                                    <div class="col-sm-12">
                                        <div class="alert alert-danger" id="errorAlert" style="display: none;"><span></span></div>
                                    </div>
                                </div>
                                <div class="row">
                                    <div class="col-sm-12">
                                        <div class="form-group td-checkin-location-edit"><label>
                                                Clock in location
                                                <span>/ Clock out location</span></label>
                                            <div class="td-select-single-outer-wrap">
                                                <div title="Telemunca" class="td-select-single">
                                                    <div class="td-select-single-button" onclick="toggleLocationDropdown()">
                                                        <span class="td-select-single-name" id="selectedLocation">Telemunca</span>
                                                    </div>
                                                    <div class="form-group td-select-list" id="locationDropdown" style="visibility: hidden;">
                                                        <div class="td-elements-list">
                                                            <div class="location-option" onclick="selectLocation('Telemunca')">Telemunca</div>
                                                            <div class="location-option" onclick="selectLocation('Birou')">Birou</div>
                                                        </div>
                                                    </div>
                                                    <input type="hidden" name="location" id="locationInput" value="Telemunca">
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="row">
                                    <div class="col-sm-12 form-group"><label>Attendance note</label>
                                        <div><input type="text" name="note" placeholder="Add note" class="form-control"></div>
                                    </div>
                                </div>
                                <hr class="td-hr-checkinout">
                                <div class="row td-date-select">
                                    <div class="col-sm-4">
                                        <div class="form-group"><label for="td-ckeck-in-out-date-65">Date<span
                                                    title="Required" class="td-user-required-field">*</span></label>
                                            <div class="td-date-input-wrap">
                                                <div class="td-date-picker">
                                                    <input id="td-ckeck-in-out-date-65" name="date"
                                                        placeholder="d/m/y" maxlength="10" type="text" autocomplete="off"
                                                        class="form-control notranslate hasDatepicker">
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="row td-time-interval-select">
                                    <div class="col-sm-4">
                                        <div title="" class="form-group"><label for="td-ckeck-in-out-start-time-65">Clock
                                                in<span title="Required" class="td-user-required-field">*</span></label>
                                            <div data-v-d6cc6db8="" class="td-time-picker"><input data-v-d6cc6db8=""
                                                    id="td-ckeck-in-out-start-time-65" name="checkin_time" placeholder="Event start"
                                                    maxlength="5" type="text" autocomplete="off"
                                                    class="form-control ui-timepicker-input notranslate"></div>
                                        </div>
                                    </div>
                                    <div class="col-sm-4">
                                        <div title="" class="form-group"><label for="td-ckeck-in-out-end-time-65">Clock
                                                out</label>
                                            <div data-v-d6cc6db8="" class="td-time-picker"><input data-v-d6cc6db8=""
                                                    id="td-ckeck-in-out-end-time-65" name="checkout_time" placeholder="Event end" maxlength="5"
                                                    type="text" autocomplete="off"
                                                    class="form-control ui-timepicker-input notranslate"></div>
                                        </div>
                                    </div>
                                    <div class="col-sm-4">
                                        <div class="form-group"><label>Total hours</label>
                                            <div class="td-input-wrap"><input type="text" disabled="disabled"
                                                    class="form-control" style="position: relative; text-align: center;">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div><span>Geolocation cannot be registered because permissions are denied.</span></div>
                            </form>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <div class="btn cancel-btn" onclick="closeModal()"><a href="#">Cancel</a></div>
                        <button class="btn modal-default-button" onclick="submitForm()">Add</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Configuration
        const eventType = "{event_type or ''}";
        const isCheckIn = eventType === "checkIn";
        const isCheckOut = eventType === "checkOut";

        // Note: Pre-filling happens in openModal() when the modal is actually visible
        // Don't pre-fill on DOMContentLoaded because the modal fields aren't visible yet


        function calculateTotalHours() {{
            const start = document.getElementById('td-ckeck-in-out-start-time-65').value;
            const end = document.getElementById('td-ckeck-in-out-end-time-65').value;

            if (start && end) {{
                try {{
                    const [startHour, startMin] = start.split(':').map(Number);
                    const [endHour, endMin] = end.split(':').map(Number);

                    let totalMinutes = (endHour * 60 + endMin) - (startHour * 60 + startMin);

                    // Handle negative values (end time next day)
                    if (totalMinutes < 0) {{
                        totalMinutes += 24 * 60;
                    }}

                    const totalHours = Math.floor(totalMinutes / 60);
                    const remainingMinutes = totalMinutes % 60;

                    const totalField = document.querySelector('input[type="text"][disabled][style*="text-align: center"]');
                    if (totalField) {{
                        totalField.value = totalHours + ':' + String(remainingMinutes).padStart(2, '0');
                    }}
                }} catch (e) {{
                    console.error('Error calculating hours:', e);
                }}
            }}
        }}

        // Auto-calculate on page load
        calculateTotalHours();

        // Recalculate when times change
        document.getElementById('td-ckeck-in-out-start-time-65').addEventListener('input', calculateTotalHours);
        document.getElementById('td-ckeck-in-out-end-time-65').addEventListener('input', calculateTotalHours);

        function openModal() {{
            document.getElementById('checkinModal').classList.add('show');

            // Read URL parameters
            const urlParams = new URLSearchParams(window.location.search);
            const dateParam = urlParams.get('date');
            const checkinParam = urlParams.get('checkin');
            const checkoutParam = urlParams.get('checkout');

            console.log('openModal called');
            console.log('URL Params:', {{ date: dateParam, checkin: checkinParam, checkout: checkoutParam }});
            console.log('Event type:', eventType, 'isCheckIn:', isCheckIn, 'isCheckOut:', isCheckOut);

            // ALWAYS pre-fill date if provided (for both checkin and checkout)
            if (dateParam) {{
                const dateField = document.getElementById('td-ckeck-in-out-date-65');
                if (dateField) {{
                    console.log('Setting date to:', dateParam);
                    dateField.value = dateParam;
                    dateField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else {{
                    console.error('Date field not found');
                }}
            }}

            // Pre-fill check-in time ONLY for checkout events (reference time)
            // For checkin events, the user/bot should type the time
            if (checkinParam && isCheckOut) {{
                const startTimeField = document.getElementById('td-ckeck-in-out-start-time-65');
                if (startTimeField) {{
                    console.log('Setting checkin time to:', checkinParam);
                    startTimeField.value = checkinParam;
                    startTimeField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else {{
                    console.error('Start time field not found');
                }}
            }} else if (isCheckIn) {{
                console.log('CheckIn event - checkin time will NOT be pre-filled (bot will type it)');
            }}

            // NEVER pre-fill checkout time - the bot needs to type it
            // (even if checkoutParam is in URL, we ignore it for pre-filling)
            console.log('Checkout time will NOT be pre-filled - bot will type it');

            // Recalculate total hours after pre-filling
            calculateTotalHours();
        }}


        function closeModal() {{
            document.getElementById('checkinModal').classList.remove('show');
        }}

        function toggleLocationDropdown() {{
            const dropdown = document.getElementById('locationDropdown');
            const isHidden = dropdown.style.visibility === 'hidden';
            dropdown.style.visibility = isHidden ? 'visible' : 'hidden';
        }}

        function selectLocation(location) {{
            document.getElementById('selectedLocation').textContent = location;
            document.getElementById('locationInput').value = location;
            document.getElementById('locationDropdown').style.visibility = 'hidden';
        }}

        function submitForm() {{
            const form = document.getElementById('checkinForm');
            const formData = new FormData(form);

            fetch('/mock-iflow/submit', {{
                method: 'POST',
                body: formData
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.status === 'success') {{
                    closeModal();
                    // Show success notification
                    const successDiv = document.createElement('div');
                    successDiv.style.cssText = 'position:fixed;top:20px;right:20px;background:#4caf50;color:white;padding:15px 25px;border-radius:4px;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,0.2);';
                    successDiv.textContent = data.message || 'Time entry recorded successfully!';
                    document.body.appendChild(successDiv);
                    setTimeout(() => successDiv.remove(), 3000);
                }} else {{
                    const errorAlert = document.getElementById('errorAlert');
                    errorAlert.querySelector('span').textContent = data.message || 'An error occurred';
                    errorAlert.style.display = 'block';
                }}
            }})
            .catch(error => {{
                const errorAlert = document.getElementById('errorAlert');
                errorAlert.querySelector('span').textContent = 'Network error: ' + error;
                errorAlert.style.display = 'block';
            }});
        }}

        // Close modal when clicking outside
        document.getElementById('checkinModal').addEventListener('click', function(e) {{
            if (e.target === this) {{
                closeModal();
            }}
        }});

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {{
            const dropdown = document.getElementById('locationDropdown');
            const button = document.querySelector('.td-select-single-button');
            if (!button.contains(e.target) && !dropdown.contains(e.target)) {{
                dropdown.style.visibility = 'hidden';
            }}
        }});
    </script>
{SIMULATION_BOT_SCRIPT}
</body>
</html>
"""


def get_success_page() -> str:
    """Generate success page after check-in/out."""
    return """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mock iFlow - Success</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }
        .success-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            max-width: 400px;
            width: 100%;
            text-align: center;
        }
        .success-icon {
            font-size: 64px;
            color: #28a745;
            margin-bottom: 20px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        p {
            color: #666;
            margin-bottom: 30px;
        }
        .success-message {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        a {
            display: inline-block;
            padding: 12px 30px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: 600;
        }
        a:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <div class="success-container">
        <div class="success-icon">✓</div>
        <h1>Pontaj Înregistrat cu Succes!</h1>
        <div class="success-message">
            Successfully recorded your time entry.
        </div>
        <p>Your check-in/check-out has been recorded successfully.</p>
        <a href="/mock-iflow/dashboard">Înapoi la Dashboard</a>
    </div>
</body>
</html>
"""
