
# AWS Untagged Resources S3 and Email report


This project use AWS CostExplorer csv reports to extract untagged resources.  Use a cloudwatch rule to execute a lambda function who read cost explorer reports (always the last 1324-aws-billing-detailed-line-items-with-resources-and-tags-yyyy-mm.csv.zip file) and generate another csv report with the untagged resources, save them on s3 and send it on an email using AWS SES service.

The architecture diagram is:

![Image arch](https://github.com/llizamab/aws-tags-monitorization/blob/master/architecture.png?raw=true)


AWS have an API called [resourcegroupstaggingapi](https://docs.aws.amazon.com/cli/latest/reference/resourcegroupstaggingapi/get-resources.html) 
but this one doesn't return resources who never have been tagged.


The purpose of this project is: based on custom tags defined on your account to identify your costs. Check automatically resources who doesn't have this custom tags, or never have been tagged.

Email and Txt template for report can be modified on files 'emailHtml.html' and 'emailText.txt'

CSV reports saved on S3 and cost explorer files are migrated to ONEZONE_IA after 30 days and deleted after 180 days. If needed remove LifecycleConfiguration on the CF definition of costsS3Bucket resource.



## Properties definitions

Before deploy, edit the next values on file serverless.yml:

- **notificationEmail** = Email where to send the reports, separated by comma if need to add more
- **senderEmail** = Email sender
- **subject** = Subject text for email report
- **bucketName** = The name of the new bucket where to store cost reports and untagged csv reports files
- **reportCron** = Cron expression for report execution. More info for sintax on: [ScheduledEvents](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html)
- **customTags** = Custom tags defined for cost explorer
- **stackTags**: Use your own tags for identify the resources this stack create on you AWS account


## Considerations

AWS SES service need to verify the emails addresses used on senderEmail and notificationEmail. 
More information on:
- [SES verify email](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-email-addresses.html)
- [SES control access](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-email-addresses.htmlhttps://docs.aws.amazon.com/es_es/ses/latest/DeveloperGuide/control-user-access.html)

On your AWS Account, billing reports 'Detailed Billing Reports [Legacy]' must be enabled and configured after deploy.
More information on: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/configurecostallocreport.html


## Usage

- Clone the repo
- Install [serverless-python-requirements](https://www.serverless.com/plugins/serverless-python-requirements)
- Deploy the stack executing
```
sls deploy
```
- On your AWS account, on Billing preference, section 'Detailed Billing Reports [Legacy]', especify the s3 bucket created with 'bucketName' and check the option 'Detailed billing report with resources and tags*'


## References:
- [aws cli](https://docs.aws.amazon.com/cli/latest/reference/configure/)
- [serverless framework](https://www.serverless.com/)
- [SES Lambda email reference](https://medium.com/@kuharan/sending-emails-with-aws-lambda-aws-simple-email-service-ses-513839bc53ab)

