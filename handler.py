
import os
import io
import pandas as pd
import json
import boto3
import time
import zipfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


def monitorization(event, context):
    try:
        # read dataset csv from s3
        dataframe = pd.read_csv(readFile())
        
        print("Columnas csv original", dataframe.keys())
        print("Shape csv original", dataframe.shape)
        
        strTags = os.environ['TAGS'].split(",")
        tagsArr = []
        for tag in strTags:
          if tag != "":
            tagsArr.append("user:" + tag)

        print("custom tags: ", tagsArr)

        # me quedo solo con las columnas que necesito
        df = dataframe[["ProductName", "ResourceId", "aws:cloudformation:stack-name", 
                   "aws:createdBy"] + tagsArr]

        print("Columnas csv filtrado", df.keys())
        print("Shape csv filtrado", df.shape)

        # filtro los datos y me quedo solo con los que no tienen tags, o que no son recursos como tales
        for tag in tagsArr:    
          df = df[df[tag].isnull()]

        dffiltrado = df[df["ResourceId"].notnull()]

        print("Columnas csv sin tags", dffiltrado.keys())
        print("Shape csv sin tags", dffiltrado.shape)
        
        # remove duplicates
        df2 = dffiltrado.drop_duplicates(subset=['ProductName', 'ResourceId',
                                                 'aws:cloudformation:stack-name',
                                                 'aws:createdBy'], keep='first')

        # elimino columnas que no uso
        df2 = df2.drop(columns=tagsArr)
        
        print("Columnas csv sin tags sin duplicados", df2.keys())
        print("Shape csv sin tags sin duplicados", df2.shape)

        # genero un csv
        fileName = time.strftime("%Y%m%d-%H%M%S") + '_untagged-resources-report.csv'
        fileDest = '/tmp/' + fileName

        df2.to_csv(fileDest, index = False)

        # guardar en S3
        writeFile(fileDest, fileName)
        
        # send email
        sender = os.environ['SENDER']
        recipient = os.environ['RECIPIENT']
        recipients = recipient.split(",")
        subject = os.environ['SUBJECT']
        messageId = send_email(sender, recipients, subject, fileDest, fileName)

        body = {
           "mensaje": fileName,
           "messageId": messageId
        }

        response = {
            "statusCode": 200,
            "body": json.dumps(body)
        }

        return response

    except Exception as exc:
        print("error no esperado:", exc)

        body = {
           "mensaje": "Exception",
           "ex": str(exc)
        }

        response = {
           "statusCode": 500,
           "body": json.dumps(body)
        }
        return response



def readFile():
   s3 = boto3.resource('s3')
   bucketName = os.environ['S3_BUCKET']
   
   print("bucketName", bucketName)
   
   bucket = s3.Bucket(bucketName)
   
   # todo, leer ultimo fichero zip y descomprimir csv
   object = get_most_recent_s3_object(bucketName)
   
   obj = bucket.Object(key=object['Key'])
   response = obj.get()
   
   path_to_zip_file = "/tmp/" + object['Key']
   
   bucket.download_file(object['Key'], path_to_zip_file)
   
   with zipfile.ZipFile(path_to_zip_file, 'r') as zip_ref:
     zip_ref.extractall('/tmp/')
     
   print("files on tmp", os.listdir('/tmp/'))
   
   print("path_to_zip_file", path_to_zip_file)
   
   path_to_csv = path_to_zip_file.replace('.zip', '')

   print("path_to_csv", path_to_csv)

   return path_to_csv



def writeFile(fileDest, fileName):
   s3 = boto3.client('s3')
   bucketName = os.environ['S3_BUCKET']

   with open(fileDest, "rb") as file:
       s3.upload_fileobj(file, bucketName, fileName)



def get_most_recent_s3_object(bucket_name):
    s3 = boto3.client('s3')
    paginator = s3.get_paginator( "list_objects_v2" )
    page_iterator = paginator.paginate(Bucket=bucket_name)
    
    latests = []
    latest = None
    
    for page in page_iterator:
        if "Contents" in page:
            
            print("page", page)
            print("page.Contents", page['Contents'])
            
            for obj in page['Contents']:

              print("obj.Key", obj['Key'])
              
              if ".csv.zip" in obj['Key']:
                print("append")
                latests.append(obj)
 
    if len(latests) > 0:
      latest = max(latests, key=lambda x: x['LastModified'])

    return latest



def send_email(sender, recipients, subject, fileDir, fileName):

    print("sending email to: ", recipients, " from: ", sender)

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = os.environ['BODY_HTML']
    # The HTML body of the email.
    BODY_HTML = os.environ['BODY_HTML']
    CHARSET = "utf-8"
    client = boto3.client('ses')
    msg = MIMEMultipart('mixed')
    # Add subject, from and to lines.
    msg['Subject'] = subject 
    msg['From'] = sender 
    msg_body = MIMEMultipart('alternative')
    textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
    htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)
    # Add the text and HTML parts to the child container.
    msg_body.attach(textpart)
    msg_body.attach(htmlpart)
    # Define the attachment part and encode it using MIMEApplication.
    att = MIMEApplication(open(fileDir, 'rb').read())
    att.add_header('Content-Disposition','attachment',filename=fileName)
    if os.path.exists(fileDir):
        print("File exists")
    else:
        print("File does not exists")
    # Attach the multipart/alternative child container to the multipart/mixed
    # parent container.
    msg.attach(msg_body)
    # Add the attachment to the parent container.
    msg.attach(att)
    try:
        #Provide the contents of the email.
        response = client.send_raw_email(
            Source=msg['From'],
            Destinations=recipients,
            RawMessage={
                'Data':msg.as_string(),
            }
        )
    # Display an error if something goes wrong. 
    except Exception as exc:
        print("error email no esperado:", exc)
        return "Error"
    else:
        return response['MessageId']

