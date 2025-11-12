# orders_service/schemas.py
from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString,
    GraphQLInt, GraphQLFloat, GraphQLList, GraphQLNonNull,
    GraphQLInputObjectType, GraphQLInputField, GraphQLBoolean,
    GraphQLArgument
)
from repository import (
    create_order, get_order, get_user_orders,
    update_order_status, request_refund, get_order_stats
)

# ========================
# TYPES
# ========================

OrderItemType = GraphQLObjectType('OrderItem', {
    'id': GraphQLField(GraphQLInt),
    'product_id': GraphQLField(GraphQLInt),
    'product_name': GraphQLField(GraphQLString),
    'product_sku': GraphQLField(GraphQLString),
    'quantity': GraphQLField(GraphQLInt),
    'unit_price': GraphQLField(GraphQLFloat),
    'total_price': GraphQLField(GraphQLFloat),
})

StatusHistoryType = GraphQLObjectType('StatusHistory', {
    'id': GraphQLField(GraphQLInt),
    'status': GraphQLField(GraphQLString),
    'changed_by': GraphQLField(GraphQLInt),
    'notes': GraphQLField(GraphQLString),
    'timestamp': GraphQLField(GraphQLString),
})

RefundType = GraphQLObjectType('Refund', {
    'id': GraphQLField(GraphQLInt),
    'amount': GraphQLField(GraphQLFloat),
    'reason': GraphQLField(GraphQLString),
    'status': GraphQLField(GraphQLString),
    'requested_at': GraphQLField(GraphQLString),
    'processed_at': GraphQLField(GraphQLString),
})

OrderType = GraphQLObjectType('Order', {
    'id': GraphQLField(GraphQLInt),
    'user_id': GraphQLField(GraphQLInt),
    'username': GraphQLField(GraphQLString),
    'email': GraphQLField(GraphQLString),
    'status': GraphQLField(GraphQLString),
    'total_amount': GraphQLField(GraphQLFloat),
    'currency': GraphQLField(GraphQLString),
    'shipping_address': GraphQLField(GraphQLString),
    'billing_address': GraphQLField(GraphQLString),
    'payment_method': GraphQLField(GraphQLString),
    'payment_status': GraphQLField(GraphQLString),
    'tracking_code': GraphQLField(GraphQLString),
    'notes': GraphQLField(GraphQLString),
    'created_at': GraphQLField(GraphQLString),
    'updated_at': GraphQLField(GraphQLString),
    'items': GraphQLField(GraphQLList(OrderItemType)),
    'status_history': GraphQLField(GraphQLList(StatusHistoryType)),
    'refunds': GraphQLField(GraphQLList(RefundType)),
})

OrderStatsType = GraphQLObjectType('OrderStats', {
    'created': GraphQLField(GraphQLInt),
    'confirmed': GraphQLField(GraphQLInt),
    'preparing': GraphQLField(GraphQLInt),
    'shipped': GraphQLField(GraphQLInt),
    'delivered': GraphQLField(GraphQLInt),
    'cancelled': GraphQLField(GraphQLInt),
    'refunded': GraphQLField(GraphQLInt),
})

# ========================
# INPUT TYPES
# ========================

OrderItemInput = GraphQLInputObjectType('OrderItemInput', {
    'product_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'quantity': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
})

CreateOrderInput = GraphQLInputObjectType('CreateOrderInput', {
    'user_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'items': GraphQLInputField(GraphQLNonNull(GraphQLList(GraphQLNonNull(OrderItemInput)))),
    'shipping_address': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'billing_address': GraphQLInputField(GraphQLString),
    'payment_method': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'notes': GraphQLInputField(GraphQLString),
})

UpdateStatusInput = GraphQLInputObjectType('UpdateStatusInput', {
    'order_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'new_status': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'changed_by': GraphQLInputField(GraphQLInt),
    'notes': GraphQLInputField(GraphQLString),
})

RefundRequestInput = GraphQLInputObjectType('RefundRequestInput', {
    'order_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'amount': GraphQLInputField(GraphQLNonNull(GraphQLFloat)),
    'reason': GraphQLInputField(GraphQLNonNull(GraphQLString)),
})

# ========================
# QUERY
# ========================

Query = GraphQLObjectType('Query', {
    'order': GraphQLField(
        OrderType,
        args={'id': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, id: get_order(id)
    ),
    'userOrders': GraphQLField(
        GraphQLList(OrderType),
        args={'user_id': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, user_id: get_user_orders(user_id)
    ),
    'orderStats': GraphQLField(
        OrderStatsType,
        resolve=lambda *_: get_order_stats()
    ),
})

# ========================
# MUTATION
# ========================

Mutation = GraphQLObjectType('Mutation', {
    # === ORDER ===
    'createOrder': GraphQLField(
        GraphQLInt,
        args={'input': GraphQLNonNull(CreateOrderInput)},
        resolve=lambda _, info, input: create_order(**input)
    ),

    'updateOrderStatus': GraphQLField(
        GraphQLBoolean,
        args={'input': GraphQLNonNull(UpdateStatusInput)},
        resolve=lambda _, info, input: update_order_status(**input)
    ),

    'cancelOrder': GraphQLField(
        GraphQLBoolean,
        args={'order_id': GraphQLNonNull(GraphQLInt), 'reason': GraphQLNonNull(GraphQLString)},
        resolve=lambda _, info, order_id, reason: update_order_status(
            order_id=order_id,
            new_status='cancelled',
            notes=reason
        )
    ),

    'confirmOrder': GraphQLField(
        GraphQLBoolean,
        args={'order_id': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, order_id: update_order_status(
            order_id=order_id,
            new_status='confirmed',
            notes="Admin tomonidan tasdiqlandi"
        )
    ),

    'shipOrder': GraphQLField(
        GraphQLBoolean,
        args={'order_id': GraphQLNonNull(GraphQLInt), 'tracking_code': GraphQLNonNull(GraphQLString)},
        resolve=lambda _, info, order_id, tracking_code: (
            update_order_status(order_id, 'shipped', notes=f"Tracking: {tracking_code}")
        )
    ),

    'deliverOrder': GraphQLField(
        GraphQLBoolean,
        args={'order_id': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, order_id: update_order_status(
            order_id=order_id,
            new_status='delivered',
            notes="Muvaffaqiyatli yetkazildi"
        )
    ),

    # === REFUND ===
    'requestRefund': GraphQLField(
        GraphQLInt,
        args={'input': GraphQLNonNull(RefundRequestInput)},
        resolve=lambda _, info, input: request_refund(**input)
    ),
})

# ========================
# SCHEMA
# ========================

schema = GraphQLSchema(query=Query, mutation=Mutation)