# -*- coding: utf-8 -*-
"""
Created on Tue Dec 23 16:22:17 2025

@author: c_piazzese
"""

import smtplib
from email.message import EmailMessage
from pathlib import Path
from app.config import settings
import base64
from io import BytesIO
import plotly.express as px
import os

def generate_html_report(results, filename):
    gender_data = results.get("genderCounts", [])
    age_data = results.get("ageGroups", [])
    ethnicity_data = results.get("ethnicityCounts", [])
    admissions_data = results.get("admissionsByMonth", [])
    diagnoses_included = results.get("diagnoses_included", [])
    diagnoses_excluded = results.get("diagnoses_excluded", [])
    admissions_month_data = results.get("admissions_by_month", [])
    
    


    html = f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <title>Cohort Results – {results['title']} </title>
      
      <style>
        body {{ font-family: Arial, sans-serif; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background-color: #f4f4f4; }}
        img {{ max-width: 600px; margin-bottom: 20px; }}
      </style>
    </head>
    <body>
      <h1 style="font-size: 42px; margin-bottom: 4px;">
          Cohort Results – {results['title']} 
          </h1>
      <p style="margin-top:10px;font-size:0.9em;color:#666;">
          Generated on {results['date_time_mail']}
      </p>
      
      <p style="font-size: 24px; margin-top: 20px;">
          <strong>Requester:</strong> {results['email']}
       </p>
      
      <p style="font-size: 24px; margin-top: 10px;">
          <strong>Total patients:</strong> {results['total_patients']}
       </p>
    """
    
    
    if results['total_patients'] > 10:
        # -------------------
        # Gender distribution
        # -------------------
        html += "<h2>Gender distribution</h2>"
    
        if len(set(g['gender'] for g in gender_data)) > 1:
            # Generate bar chart with Plotly
            df_gender = {g['gender']: g['count'] for g in gender_data}
            fig = px.bar(x=list(df_gender.keys()), y=list(df_gender.values()), labels={'x':'Gender','y':'Count'})
            buf = BytesIO()
            fig.write_image(buf, format="png")
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            html += f'<img src="data:image/png;base64,{img_b64}"/>'
    
        # Add table
        html += """
        <table>
          <tr><th>Gender</th><th>Count</th></tr>
          {}
        </table>
        """.format(''.join(f"<tr><td>{g['gender']}</td><td>{g['count']}</td></tr>" for g in gender_data))
    
        # -------------------
        # Age distribution
        # -------------------
        html += "<h2>Age distribution</h2>"
    
        if len({a["range"] for a in age_data}) > 1:
            fig = px.bar(
                x=[a["range"] for a in age_data],
                y=[a["count"] for a in age_data],
                labels={"x": "Age range", "y": "Count"}
            )
            buf = BytesIO()
            fig.write_image(buf, format="png")
            html += f'<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"/>'
    
        html += """
        <table>
          <tr><th>Age range</th><th>Count</th></tr>
          {}
        </table>
        """.format("".join(
            f"<tr><td>{a['range']}</td><td>{a['count']}</td></tr>"
            for a in age_data
        ))
                 
                 
        # -------------------
        # Ethnicity distribution
        # -------------------
        html += "<h2>Ethnicity distribution</h2>"
    
        if len(set(e['ethnicity'] for e in ethnicity_data)) > 1:
            df_eth = {e['ethnicity']: e['count'] for e in ethnicity_data}
            fig = px.pie(values=list(df_eth.values()), names=list(df_eth.keys()))
            buf = BytesIO()
            fig.write_image(buf, format="png")
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            html += f'<img src="data:image/png;base64,{img_b64}"/>'
    
        # Add table
        html += """
        <table>
          <tr><th>Ethnicity</th><th>Count</th></tr>
          {}
        </table>
        """.format(''.join(f"<tr><td>{e['ethnicity']}</td><td>{e['count']}</td></tr>" for e in ethnicity_data))
        
        # -------------------
        # Admissions by Month-Year (TABLE ONLY)
        # -------------------
        html += "<h2>Admissions by Month-Year</h2>"
        html += """
        <table>
          <tr><th>Month-Year</th><th>Admissions</th></tr>
          {}
        </table>
        """.format("".join(
            f"<tr><td>{m['monthYear']}</td><td>{m['count']}</td></tr>"
            for m in admissions_month_data
        ))
        
        if diagnoses_included:     
            # -------------------
            # Diagnoses included (TABLE ONLY with counts)
            # -------------------
            html += "<h2>Diagnoses included</h2>"
            html += """
            <table>
              <tr><th>Diagnosis</th><th>Admissions</th></tr>
              {}
            </table>
            """.format("".join(
                f"<tr><td>{d['diagnosis']}</td><td>{d['count']}</td></tr>"
                for d in diagnoses_included
            ))
             
        if diagnoses_excluded:
            # -------------------
            # Diagnoses excluded (names only)
            # -------------------
            html += "<h2>Diagnoses excluded</h2>"
            html += """
            <table>
              <tr><th>Diagnosis</th></tr>
              {}
            </table>
            """.format(
                "".join(
                    f"<tr><td>{d}</td></tr>"
                    for d in diagnoses_excluded
                )
            )
                 
                 
        # -------------------
        # Footer
        # -------------------
        html += """
        </body>
        </html>
        """

    # Save HTML
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)



def send_results_email(
    to_email: str,
    subject: str,
    html_body: str,
    sender_email: str,
    smtp_server: str,
    smtp_port: int,
    app_password: str,
    output_folder: str,
    cohort_title = str,
    data_and_time = str,
    html_attachment_path: Path | None = None,
):
    # ---- Build email ----
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Plaintext + HTML
    msg.set_content("Your email client does not support HTML.")
    msg.add_alternative(html_body, subtype="html")

    # Attach the HTML file if needed
    if html_attachment_path and html_attachment_path.exists():
        msg.add_attachment(
            html_attachment_path.read_bytes(),
            maintype="text",
            subtype="html",
            filename=html_attachment_path.name,
        )

    # ---- Send email (STARTTLS only) ----
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # REQUIRED
            server.login(sender_email, app_password)
            server.send_message(msg)

    except Exception as e:
        print(f"Failed to send email: {e}")

        failure_filename = os.path.join(output_folder,
                f"{cohort_title.replace(' ', '_')}_results_html_{data_and_time}_failure.txt"
            )
        
        with open(failure_filename, "w") as f:
            f.write(f"Email sending failed\n")
            f.write(f"Recipient: {to_email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Error: {e}\n")