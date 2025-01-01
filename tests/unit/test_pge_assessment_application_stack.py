import aws_cdk as core
import aws_cdk.assertions as assertions

from pge_assessment_application.pge_assessment_application_stack import PgeAssessmentApplicationStack

# example tests. To run these tests, uncomment this file along with the example
# resource in pge_assessment_application/pge_assessment_application_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = PgeAssessmentApplicationStack(app, "pge-assessment-application")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
