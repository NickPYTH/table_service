from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        print(request)
        return JsonResponse({'user': 'kek'})
