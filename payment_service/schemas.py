# payments_service/schemas.py
from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString,
    GraphQLInt, GraphQLFloat, GraphQLList, GraphQLNonNull,
    GraphQLInputObjectType, GraphQLInputField, GraphQLBoolean,
    GraphQLArgument
)
from repository import (
    create_payment, verify_payment, request_refund, process_refund,
    get_payment_methods, get_payment_stats, get_payment
)

# ========================
# TYPES
# ========================

PaymentMethodType = GraphQLObjectType('PaymentMethod', {
    'id': GraphQLField(GraphQLInt),
    'name': GraphQLField(GraphQLString),
    'display_name': GraphQLField(GraphQLString),
})

PaymentLogType = GraphQLObjectType('PaymentLog', {
    'id': GraphQLField(GraphQLInt),
    'status': GraphQLField(GraphQLString),
    'message': GraphQLField(GraphQLString),
    'timestamp': GraphQLField(GraphQLString),
})

RefundType = GraphQLObjectType('Refund', {
    'id': GraphQLField(GraphQLInt),
    'amount': GraphQLField(GraphQLFloat),
    'reason': GraphQLField(GraphQLString),
    'status': GraphQLField(GraphQLString),
    'gateway_refund_id': GraphQLField(GraphQLString),
    'requested_at': GraphQLField(GraphQLString),
    'processed_at': GraphQLField(GraphQLString),
})

PaymentType = GraphQLObjectType('Payment', {
    'id': GraphQLField(GraphQLInt),
    'order_id': GraphQLField(GraphQLInt),
    'method_name': GraphQLField(GraphQLString),
    'display_name': GraphQLField(GraphQLString),
    'amount': GraphQLField(GraphQLFloat),
    'currency': GraphQLField(GraphQLString),
    'status': GraphQLField(GraphQLString),
    'gateway_transaction_id': GraphQLField(GraphQLString),
    'payer_info': GraphQLField(GraphQLString),  # JSON string
    'error_message': GraphQLField(GraphQLString),
    'created_at': GraphQLField(GraphQLString),
    'updated_at': GraphQLField(GraphQLString),
    'logs': GraphQLField(GraphQLList(PaymentLogType)),
    'refunds': GraphQLField(GraphQLList(RefundType)),
})

PaymentStatsType = GraphQLObjectType('PaymentStats', {
    'pending': GraphQLField(GraphQLInt),
    'paid': GraphQLField(GraphQLInt),
    'failed': GraphQLField(GraphQLInt),
    'refunded': GraphQLField(GraphQLInt),
})

CreatePaymentResultType = GraphQLObjectType('CreatePaymentResult', {
    'payment_id': GraphQLField(GraphQLInt),
    'payment_url': GraphQLField(GraphQLString),
    'transaction_id': GraphQLField(GraphQLString),
})

VerifyPaymentResultType = GraphQLObjectType('VerifyPaymentResult', {
    'status': GraphQLField(GraphQLString),
    'amount': GraphQLField(GraphQLFloat),
    'success': GraphQLField(GraphQLBoolean),
})

# ========================
# INPUT TYPES
# ========================

PayerInfoInput = GraphQLInputObjectType('PayerInfoInput', {
    'email': GraphQLInputField(GraphQLString),
    'phone': GraphQLInputField(GraphQLString),
    'name': GraphQLInputField(GraphQLString),
})

CreatePaymentInput = GraphQLInputObjectType('CreatePaymentInput', {
    'order_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'method': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'amount': GraphQLInputField(GraphQLNonNull(GraphQLFloat)),
    'payer_info': GraphQLInputField(PayerInfoInput),
})

VerifyPaymentInput = GraphQLInputObjectType('VerifyPaymentInput', {
    'payment_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'token': GraphQLInputField(GraphQLNonNull(GraphQLString)),
})

RefundRequestInput = GraphQLInputObjectType('RefundRequestInput', {
    'payment_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'amount': GraphQLInputField(GraphQLNonNull(GraphQLFloat)),
    'reason': GraphQLInputField(GraphQLNonNull(GraphQLString)),
})

ProcessRefundInput = GraphQLInputObjectType('ProcessRefundInput', {
    'refund_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'status': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'gateway_refund_id': GraphQLInputField(GraphQLString),
})

# ========================
# QUERY
# ========================

Query = GraphQLObjectType('Query', {
    'paymentMethods': GraphQLField(
        GraphQLList(PaymentMethodType),
        resolve=lambda *_: get_payment_methods()
    ),
    'payment': GraphQLField(
        PaymentType,
        args={'id': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, id: get_payment(id)
    ),
    'paymentStats': GraphQLField(
        PaymentStatsType,
        resolve=lambda *_: get_payment_stats()
    ),
})

# ========================
# MUTATION
# ========================

Mutation = GraphQLObjectType('Mutation', {
    # === TO'LOV YARATISH ===
    'createPayment': GraphQLField(
        CreatePaymentResultType,
        args={'input': GraphQLNonNull(CreatePaymentInput)},
        resolve=lambda _, info, input: create_payment(**input)
    ),

    # === TO'LOV TEKSHIRISH ===
    'verifyPayment': GraphQLField(
        VerifyPaymentResultType,
        args={'input': GraphQLNonNull(VerifyPaymentInput)},
        resolve=lambda _, info, input: verify_payment(**input)
    ),

    # === QAYTARISH ===
    'requestRefund': GraphQLField(
        GraphQLInt,
        args={'input': GraphQLNonNull(RefundRequestInput)},
        resolve=lambda _, info, input: request_refund(**input)
    ),

    'processRefund': GraphQLField(
        GraphQLBoolean,
        args={'input': GraphQLNonNull(ProcessRefundInput)},
        resolve=lambda _, info, input: process_refund(**input)
    ),
})

# ========================
# SCHEMA
# ========================

schema = GraphQLSchema(query=Query, mutation=Mutation)