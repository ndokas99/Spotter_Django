from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .services.route_planner import get_route, get_fuel_checkpoints
from .services.fuel_optimizer import plan_fuel_stops, compute_fuel_cost


class PlanRouteView(APIView):
    def get(self, request):
        return Response({"message": "Use POST method"})

    def post(self, request):
        try:
            start = request.data.get("start")
            end = request.data.get("end")

            if not start or not end:
                return Response({"error": "Missing start or end coordinates."}, status=400)

            route = get_route(start, end)
            checkpoints = get_fuel_checkpoints(route["geometry"])
            fuel_stops = plan_fuel_stops(checkpoints)
            total_cost, breakdown = compute_fuel_cost(route["distance_miles"], fuel_stops)

            return Response({
                "route": route["geometry"],
                "fuel_cost": total_cost,
                "fuel_stops": breakdown
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

