from flask import Flask, render_template, request, send_file
import pdfkit
import os
from datetime import datetime
import qrcode
import uuid
import csv
from pathlib import Path

app = Flask(__name__)

# Configure path to wkhtmltopdf executable
PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

@app.route('/')
def index():
    return render_template('index.html')

def to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def assign_employee_id():
    return f"EMP-{uuid.uuid4().hex[:6].upper()}"

def calculate_net_pay(data):
    try:
        hours_worked = to_float(data.get('hours_worked'))
        hourly_rate = to_float(data.get('hourly_rate'))
        ot_hours = to_float(data.get('ot_hours'))
        ot_rate = to_float(data.get('ot_rate', 1.25))
        bonus = to_float(data.get('bonus'))

        regular_pay = hours_worked * hourly_rate
        ot_pay = ot_hours * (hourly_rate * ot_rate)
        earnings = regular_pay + ot_pay + bonus

        tax = to_float(data.get('tax'))
        sss = to_float(data.get('sss'))
        pagibig = to_float(data.get('pagibig'))
        philhealth = to_float(data.get('philhealth'))
        deductions = 0 if data.get('voluntary') else tax + sss + pagibig + philhealth

        data['regular_pay'] = f"{regular_pay:,.2f}"
        data['ot_pay'] = f"{ot_pay:,.2f}"
        data['earnings'] = f"{earnings:,.2f}"
        data['deductions'] = f"{deductions:,.2f}"

        net_pay = earnings - deductions
        data['net_pay_value'] = net_pay
        return f"{net_pay:,.2f}"
    except Exception as e:
        print("Error calculating net pay:", e)
        return "0.00"
    except Exception as e:
        print("Error calculating net pay:", e)
        return "0.00"

@app.route('/generate', methods=['POST'])
def generate():
    data = request.form.to_dict()
    data['employee_id'] = assign_employee_id()
    data['voluntary'] = 'voluntary' in request.form
    data['net_pay'] = calculate_net_pay(data)
    data['date_issued'] = datetime.strptime(data['pay_period'], '%Y-%m-%d').strftime('%B %d, %Y')

    logo = request.files.get('logo')
    logo_path = None
    if logo and logo.filename != '':
        local_logo_path = os.path.join('static', 'logo.png')
        logo.save(local_logo_path)
        logo_path = Path(local_logo_path).resolve().as_uri()

    unique_id = str(uuid.uuid4())[:8]
    data['payslip_id'] = unique_id
    qr_img = qrcode.make(f"Payslip ID: {unique_id}")
    qr_path_local = os.path.join('static', f'{unique_id}_qr.png')
    qr_img.save(qr_path_local)
    qr_path = Path(qr_path_local).resolve().as_uri()

    rendered = render_template('payslip.html', data=data, logo_path=logo_path, qr_path=qr_path)
    pdf_path = f"payslip_{data.get('employee_name', 'employee')}_{data['date_issued'].replace(' ', '_')}.pdf"
    pdfkit.from_string(rendered, pdf_path, configuration=PDFKIT_CONFIG, options={'enable-local-file-access': ''})
    return send_file(pdf_path, as_attachment=True)

@app.route('/bulk-generate', methods=['POST'])
def bulk_generate():
    file = request.files['csv_file']
    if file:
        filepath = os.path.join('uploads', file.filename)
        file.save(filepath)

        with open(filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                row['employee_id'] = assign_employee_id()
                row['voluntary'] = row.get('voluntary', '').lower() == 'true'
                row['net_pay'] = calculate_net_pay(row)
                row['date_issued'] = datetime.now().strftime('%B %d, %Y')

                unique_id = str(uuid.uuid4())[:8]
                row['payslip_id'] = unique_id
                qr_img = qrcode.make(f"Payslip ID: {unique_id}")
                qr_path_local = os.path.join('static', f'{unique_id}_qr.png')
                qr_img.save(qr_path_local)
                qr_path = Path(qr_path_local).resolve().as_uri()

                rendered = render_template('payslip.html', data=row, logo_path=None, qr_path=qr_path)
                pdf_path = f"payslip_{data.get('employee_name', 'employee').upper().replace(' ', '_')}_{data['date_issued'].replace(' ', '_')}.pdf"
                pdfkit.from_string(rendered, pdf_path, configuration=PDFKIT_CONFIG, options={'enable-local-file-access': ''})

        return "Bulk payslips generated successfully."

if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
