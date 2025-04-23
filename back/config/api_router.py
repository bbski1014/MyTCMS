from rest_framework.routers import DefaultRouter
from apps.users.views import UserViewSet
from apps.projects.views import ProjectViewSet # Assuming ProjectViewSet exists
from apps.testcases.views import TestCaseViewSet
from apps.executions.views import TestPlanViewSet, TestRunViewSet, TestResultViewSet # Assuming these exist
# ... other viewset imports ...

router = DefaultRouter()

router.register("users", UserViewSet)
router.register("projects", ProjectViewSet)
router.register("testcases", TestCaseViewSet)
router.register("testplans", TestPlanViewSet) # Assuming testplans endpoint
router.register("testruns", TestRunViewSet)   # Assuming testruns endpoint
router.register("testresults", TestResultViewSet) # Assuming testresults endpoint

# ... potentially nested routers if used ...

app_name = "api"
urlpatterns = router.urls 