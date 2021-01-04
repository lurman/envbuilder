import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailSender:
    def __init__(self, server, port, sender, password):
        if server and port and sender and password:
            self.smtp_server = server
            self.port = port
            self.sender_email = sender
            self.password = password
        else:
            self.smtp_server = "smtp.gmail.com"
            self.port = 587  # For starttls
            self.sender_email = "snc.envbuilder@gmail.com"
            self.password = "ServiceNow2020"

    def send_message(self, recipient_address, subject, text, status):
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = self.sender_email
        message["To"] = recipient_address
        current_color = 'green'
        if status is False:
            current_color = 'red'
        html = """\
        <html>
          <body>
            <p style="color:{0};font-size:20px">""".format(current_color) + text.replace('\n', '<br>') + """</p><br>
          </body>
        </html>
        """
        body = MIMEText(html, "html")
        message.attach(body)


        # Create a secure SSL context
        context = ssl.create_default_context()

        # Try to log in to server and send email
        try:
            server = smtplib.SMTP(self.smtp_server, self.port)
            server.ehlo() # Can be omitted
            server.starttls() # Secure the connection
            server.login(self.sender_email, self.password)
            server.sendmail(
                self.sender_email, recipient_address, message.as_string()
            )
        except Exception as e:
            # Print any error messages to stdout
            print(e)
        finally:
            server.quit()


