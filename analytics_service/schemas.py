# analytics_service/schemas.py
from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString,
    GraphQLInt, GraphQLFloat, GraphQLList, GraphQLNonNull
)
from repository import get_dashboard_stats, get_top_products, get_revenue_trend

# TYPES
DailyStatsType = GraphQLObjectType('DailyStats', {
    'date': GraphQLField(GraphQLString),
    'total_orders': GraphQLField(GraphQLInt),
    'total_revenue': GraphQLField(GraphQLFloat),
    'new_users': GraphQLField(GraphQLInt),
    'top_product_name': GraphQLField(GraphQLString),
})

ProductSalesType = GraphQLObjectType('ProductSales', {
    'name': GraphQLField(GraphQLString),
    'sales': GraphQLField(GraphQLFloat),
})

RevenueDayType = GraphQLObjectType('RevenueDay', {
    'date': GraphQLField(GraphQLString),
    'total_revenue': GraphQLField(GraphQLFloat),
})

# QUERY
Query = GraphQLObjectType('Query', {
    'dashboard': GraphQLField(DailyStatsType, resolve=lambda *_: get_dashboard_stats()),
    'topProducts': GraphQLField(GraphQLList(ProductSalesType), args={'limit': GraphQLInt}, resolve=lambda _, i, limit=10: get_top_products(limit)),
    'revenueTrend': GraphQLField(GraphQLList(RevenueDayType), args={'days': GraphQLInt}, resolve=lambda _, i, days=7: get_revenue_trend(days)),
})

schema = GraphQLSchema(query=Query)