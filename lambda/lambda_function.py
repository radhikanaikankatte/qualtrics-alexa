# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils
import os
import requests
import re

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_intent_name, get_dialog_state, get_slot_value

from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

surveyId = "<Survey ID>"
apiToken = '<Qualtrics API token>'
dataCenter = '<Qualtrics Datacenter>'

def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    cleantext = cleantext.replace("&nbsp;", " ")
    return cleantext

def isNPSQuestion(currentQuestionDetails):
    value = False
    if currentQuestionDetails['type'] == 'mc' and len(currentQuestionDetails['options']['columnLabels']) == 2 and currentQuestionDetails['display'].startswith('On a scale from'):
        value = True
        
    return value

def isMCQuestion(currentQuestionDetails):
    value = False
    print(str(currentQuestionDetails))
    if currentQuestionDetails['type'] == 'mc':
        value = True
    
    return value

def isTextQuestion(currentQuestionDetails):
    value = False
    if currentQuestionDetails['type'] == 'te':
        value = True
    
    return value

def isDBQuestion(currentQuestionDetails):
    value = False
    if currentQuestionDetails['type'] == 'db':
        value = True
    
    return value

def isYesNoQuestion(currentQuestionDetails):
    value = False
    if isMCQuestion(currentQuestionDetails):
        if (currentQuestionDetails['choices']) and (len(currentQuestionDetails['choices']) == 2) and (cleanhtml(currentQuestionDetails['choices'][0]['display']) == "Yes") and (cleanhtml(currentQuestionDetails['choices'][1]['display']) == "No"):
            value = True 
    
    return value

def getCurrentQuestionText(currentQuestionDetails, questionNumber):
    currentQuestionText = cleanhtml(currentQuestionDetails['display'])
    print(currentQuestionText)
    
    questionNumberText = ""
    
    if questionNumber == 0 :
        questionNumberText = "first"
        
    else : 
        questionNumberText =  "next"
        
    if isMCQuestion(currentQuestionDetails):
        if isYesNoQuestion(currentQuestionDetails):
            currentQuestionOptionText = "Say Yes or No. "
            
        elif isNPSQuestion(currentQuestionDetails):
            noOfChoices = len(currentQuestionDetails['choices'])
            print(str(noOfChoices) + 'choices')
            columnLabels = currentQuestionDetails['options']['columnLabels']
            print(columnLabels)
            currentQuestionOptionText = "with zero being " + columnLabels[0] + " and " + str(noOfChoices - 1) + " being " + columnLabels[1]
        
        else:
            currentQuestionOptionText = 'Your options are, '
            currentQuestionOptions = currentQuestionDetails['choices']
            for index,option in enumerate(currentQuestionOptions):
                currentQuestionOptionText = currentQuestionOptionText + "Option number " + str(option['choiceId']) + ", " + cleanhtml(option['display']) + ". "
            
            currentQuestionOptionText = currentQuestionOptionText + "Say your option number."
                
        currentQuestionText = currentQuestionText + " " + currentQuestionOptionText 
        print(currentQuestionOptionText)
        
        fullSpeakOutput = "Here is your " + questionNumberText + " question, " + currentQuestionText
        
    elif currentQuestionDetails['type'] == 'te':
        # fullSpeakOutput = "Here is your " + questionNumberText + " question, " + currentQuestionText
        fullSpeakOutput = currentQuestionText
        
    elif currentQuestionDetails['type'] == 'db':
        fullSpeakOutput = currentQuestionText
        
    return fullSpeakOutput

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Welcome, if you would like to answer our survey now, please say start survey."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Welcome, if you would like to answer our survey now, please say start survey."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class StartSurveyIntentHandler(AbstractRequestHandler):
    """Handler for Answer Survey Intent"""
    def can_handle(self, handler_input):
        #type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("StartSurvey")(handler_input)
        
    def handle(self, handler_input):
        # Get any existing attributes from the incoming request
        session_attr = handler_input.attributes_manager.session_attributes
            
        # type: (HandlerInput) -> response
        #create a qualtrics survey session
        baseUrl = "https://{0}.qualtrics.com/API/v3/surveys/{1}/sessions".format(dataCenter, surveyId)
        headers = {
            "x-api-token": apiToken,
            "Content-Type": "application/json"
            }

        data = { 
          "language": "EN",
          "embeddedData": {
        	   "storeId": "48123"
        	 }
        }
        
        resp = requests.post(baseUrl, json=data, headers=headers)
        
        response_data = resp.json();
        
        #record session id and questions in session attributes
        session_attr["sessionId"] = response_data['result']['sessionId']
        
        questions = response_data['result']['questions']
        #remove db type questions as they are not answerable. Supported type of questions for conv API are mc and te
        # for question in questions:
        #     if question['type'] == 'db':
        #         questions.remove(question)
                
        session_attr["questions"] = questions
        session_attr["numberOfQuestions"] = len(questions) 
        session_attr["numberOfQuestionsAnswered"] = 0 
        session_attr["currentQuestionNumber"] = 0 
        
        currentQuestionDetails = session_attr["questions"][session_attr["currentQuestionNumber"]]
        session_attr["currentQuestionType"] = {"yesno" : isYesNoQuestion(currentQuestionDetails),
                                                "option" : isMCQuestion(currentQuestionDetails) and not(isYesNoQuestion(currentQuestionDetails)),
                                                "te" : isTextQuestion(currentQuestionDetails)
                                                }
        
        full_speak_output = getCurrentQuestionText(currentQuestionDetails, session_attr["currentQuestionNumber"])
        reprompt_speak_output = "I dint quite get that. " + getCurrentQuestionText(currentQuestionDetails, session_attr["currentQuestionNumber"])

        return (
            handler_input.response_builder
                .speak(full_speak_output)
                .ask(reprompt_speak_output)
                .response
        )


class AnswerQuestionIntentHandler(AbstractRequestHandler):
    """Handler for Answer Survey Intent"""
    def can_handle(self, handler_input):
        #type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AnswerOptionQuestion")(handler_input) or ask_utils.is_intent_name("AnswerTEQuestion")(handler_input) or ask_utils.is_intent_name("AnswerYesNoQuestion")(handler_input)
        
    def handle(self, handler_input):
        # Get any existing attributes from the incoming request
        session_attr = handler_input.attributes_manager.session_attributes
        
        # Get the slot value from the request and add it to the session 
        # attributes dictionary. Because of the dialog model and dialog 
        # delegation, this code only ever runs when the favoriteColor slot 
        # contains a value, so a null check is not necessary.
        slots = handler_input.request_envelope.request.intent.slots
        
        if "reply" in slots.keys():
            reply = slots['reply']
            session_attr["current_reply"] = reply
            if(reply.value):
                print("reply:"+ reply.value)
            
        if "optionId" in slots.keys():
            optionId = slots['optionId']
            session_attr["current_optionId"] = optionId
            if(optionId.value):
                print("option:"+ optionId.value)
            
        if "yesno" in slots.keys():
            yesno = slots['yesno'].resolutions.resolutions_per_authority[0].values[0].value.id
            session_attr["current_yesno"] = yesno
            
        if "answer" in slots.keys():
            answer = slots['answer']
            session_attr["current_answer"] = answer
            if(answer.value):
                print("answer:"+ answer.value)
            
        if "sessionId" in session_attr:
            print(session_attr["sessionId"])
            
            baseUrl = "https://{0}.qualtrics.com/API/v3/surveys/{1}/sessions/{2}".format(dataCenter, surveyId, session_attr["sessionId"])
            headers = {
                "x-api-token": apiToken,
                "Content-Type": "application/json"
                }

            data = { 
              "responses": {}
            }
            
            if "questions" in session_attr and "numberOfQuestions" in session_attr and "currentQuestionNumber" in session_attr:
                current_question_details = session_attr["questions"][session_attr["currentQuestionNumber"]]
                qId = current_question_details['questionId']
                print("current question:" + qId)
                
                if session_attr["currentQuestionType"]["yesno"]:
                    answer = {}
                    print(str(session_attr["current_yesno"]))
                    answer[session_attr["current_yesno"]] = {
                            "selected": True
                        }
                elif session_attr["currentQuestionType"]["option"]:
                    answer = {}
                    answer[session_attr["current_optionId"].value] = {
                            "selected": True
                        }
                elif session_attr["currentQuestionType"]["te"]:
                    if session_attr["current_answer"] and session_attr["current_answer"].value:
                        answer = session_attr["current_answer"].value
                    elif session_attr["current_reply"] and session_attr["current_reply"].value:
                        answer = session_attr["current_reply"].value
                
                data["responses"][qId] = answer
                
                if session_attr["currentQuestionNumber"] == len(session_attr["questions"]) - 1:
                    data["advance"] = True
                    session_attr["advance"] = True
                else :
                    data["advance"] = False
                    session_attr["advance"] = False
                
                
                response = requests.post(baseUrl, json=data, headers=headers)
                response_data = response.json()
                print(str(response_data))
                
                if session_attr["advance"] == False and response_data['result']['responses'][qId]:
                    #update counter to next question
                    session_attr["currentQuestionNumber"] = session_attr["currentQuestionNumber"] + 1
                    session_attr["numberOfQuestionsAnswered"] = session_attr["numberOfQuestionsAnswered"] + 1
                    
                    currentQuestionDetails = session_attr["questions"][session_attr["currentQuestionNumber"]]
                    session_attr["currentQuestionType"] = {"yesno" : isYesNoQuestion(currentQuestionDetails),
                                                            "option" : isMCQuestion(currentQuestionDetails) and not(isYesNoQuestion(currentQuestionDetails)),
                                                            "te" : isTextQuestion(currentQuestionDetails),
                                                            "db" : isDBQuestion(currentQuestionDetails)
                                                            }
                    
                    
                    question_speak_output = getCurrentQuestionText(currentQuestionDetails, session_attr["currentQuestionNumber"])
                    
                    reprompt_speak_output = "I dint quite get that. " + question_speak_output
                    full_speak_output = "Your answer has been recorded. " + question_speak_output
                    
                    
                    return (
                    handler_input.response_builder
                        .speak(full_speak_output)
                        .ask(reprompt_speak_output)
                        .response
                        )
                
                elif session_attr["advance"] == True and response_data['result']['done']:
                    session_attr["numberOfQuestionsAnswered"] = session_attr["numberOfQuestionsAnswered"] + 1
                    
                    full_speak_output = cleanhtml(response_data['result']['done']) + " Goodbye!"
                    
                    return (
                    handler_input.response_builder
                        .speak(full_speak_output)
                        .response
                        )
                        
                elif session_attr["advance"] == True and response_data['result']['done'] == False and response_data['result']['questions']:
                    session_attr["numberOfQuestionsAnswered"] = session_attr["numberOfQuestionsAnswered"] + 1
                    
                    print("nu of Qs: "+ str(len(session_attr["questions"])))
                    session_attr["questions"].extend(response_data['result']['questions'])
                    session_attr["numberOfQuestions"] = len(session_attr["questions"]) 
                    print("nu of Qs: "+ str(session_attr["numberOfQuestions"]))
                    
                    session_attr["currentQuestionNumber"] = session_attr["currentQuestionNumber"] + 1
                    
                    currentQuestionDetails = session_attr["questions"][session_attr["currentQuestionNumber"]]
                    print(str(currentQuestionDetails))
                    session_attr["currentQuestionType"] = {"yesno" : isYesNoQuestion(currentQuestionDetails),
                                                            "option" : isMCQuestion(currentQuestionDetails) and not(isYesNoQuestion(currentQuestionDetails)),
                                                            "te" : isTextQuestion(currentQuestionDetails),
                                                            "db" : isDBQuestion(currentQuestionDetails)
                                                            }
                    
                    
                    question_speak_output = getCurrentQuestionText(currentQuestionDetails, session_attr["currentQuestionNumber"])
                    
                    reprompt_speak_output = "I dint quite get that. " + question_speak_output
                    full_speak_output = "Your answer has been recorded. " + question_speak_output
                    
                    
                    return (
                    handler_input.response_builder
                        .speak(full_speak_output)
                        .ask(reprompt_speak_output)
                        .response
                        )
                    
                
                else: 
                    return (
                    handler_input.response_builder
                        .speak("There was an issue recording your answer. Please say, start survey, to restart your survey")
                        .ask("There was an issue recording your answer. Please say, start survey, to restart your survey")
                        .response
                    )
                
                
            
        else:
            # The user must have invoked this intent before they start survey. 
            # Trigger the Start Survey Intent
            return handler_input.response_builder.speak(
                "You need to start the survey first. Please say start survey.").ask(
                "Please say start survey.").response
        
class FallbackIntentHandler(AbstractRequestHandler):
    """Handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input))

    def handle(self, handler_input):
        # Get any existing attributes from the incoming request
        session_attr = handler_input.attributes_manager.session_attributes
        
        if session_attr["numberOfQuestionsAnswered"] < session_attr["numberOfQuestions"]:
            currentQuestionDetails = session_attr["questions"][session_attr["currentQuestionNumber"]]
            session_attr["currentQuestionType"] = {"yesno" : isYesNoQuestion(currentQuestionDetails),
                                                        "option" : isMCQuestion(currentQuestionDetails) and not(isYesNoQuestion(currentQuestionDetails)),
                                                        "te" : isTextQuestion(currentQuestionDetails),
                                                        "db" : isDBQuestion(currentQuestionDetails)
                                                    }
                    
                    
            question_speak_output = getCurrentQuestionText(currentQuestionDetails, session_attr["currentQuestionNumber"])
            full_speak_output = "I dint quite get that. " + question_speak_output
                    
            return (
                    handler_input.response_builder
                        .speak(full_speak_output)
                        .ask(question_speak_output)
                        .response
                        )
        else:
            full_speak_output = "Your survey is complete! Thank you and goodbye"
            return (
                handler_input.response_builder
                    .speak(full_speak_output)
                    .response)
        return (
                    handler_input.response_builder
                        .speak("There was an issue. Please say, start survey, to restart your survey")
                        .ask("There was an issue. Please say, start survey, to restart your survey")
                        .response
                    )



class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(StartSurveyIntentHandler())
sb.add_request_handler(AnswerQuestionIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()