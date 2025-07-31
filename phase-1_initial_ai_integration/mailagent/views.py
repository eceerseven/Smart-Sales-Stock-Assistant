from django.http import JsonResponse
from .smolagent_package.agent import ReminderAgent

def agent_run_view(request):
    agent = ReminderAgent(name="SalesReminderBot")
    result = agent.run()
    memory = agent.recall()
    return JsonResponse({
        "response": result,
        "memory": memory
    })