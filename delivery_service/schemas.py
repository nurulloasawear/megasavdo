# delivery_service/schemas.py
from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString,
    GraphQLInt, GraphQLFloat, GraphQLList, GraphQLNonNull,
    GraphQLInputObjectType, GraphQLInputField, GraphQLBoolean
)
from repository import (
    get_delivery_methods, save_address, get_user_addresses,
    create_delivery, update_delivery_status, get_delivery
)

# TYPES
DeliveryMethodType = GraphQLObjectType('DeliveryMethod', {
    'id': GraphQLField(GraphQLInt),
    'name': GraphQLField(GraphQLString),
    'display_name': GraphQLField(GraphQLString),
    'price': GraphQLField(GraphQLFloat),
    'estimated_days': GraphQLField(GraphQLString),
})

AddressType = GraphQLObjectType('Address', {
    'id': GraphQLField(GraphQLInt),
    'full_name': GraphQLField(GraphQLString),
    'phone': GraphQLField(GraphQLString),
    'region': GraphQLField(GraphQLString),
    'city': GraphQLField(GraphQLString),
    'address_line': GraphQLField(GraphQLString),
    'postal_code': GraphQLField(GraphQLString),
    'is_default': GraphQLField(GraphQLBoolean),
})

DeliveryType = GraphQLObjectType('Delivery', {
    'id': GraphQLField(GraphQLInt),
    'order_id': GraphQLField(GraphQLInt),
    'status': GraphQLField(GraphQLString),
    'tracking_code': GraphQLField(GraphQLString),
    'estimated_delivery': GraphQLField(GraphQLString),
    'display_name': GraphQLField(GraphQLString),
    'full_name': GraphQLField(GraphQLString),
    'address_line': GraphQLField(GraphQLString),
})

# INPUTS
AddressInput = GraphQLInputObjectType('AddressInput', {
    'full_name': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'phone': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'region': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'city': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'address_line': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'postal_code': GraphQLInputField(GraphQLString),
    'is_default': GraphQLInputField(GraphQLBoolean),
})

CreateDeliveryInput = GraphQLInputObjectType('CreateDeliveryInput', {
    'order_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'method_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'address_id': GraphQLInputField(GraphQLNonNull(GraphQLInt)),
    'notes': GraphQLInputField(GraphQLString),
})

# QUERY
Query = GraphQLObjectType('Query', {
    'deliveryMethods': GraphQLField(GraphQLList(DeliveryMethodType), resolve=lambda *_: get_delivery_methods()),
    'userAddresses': GraphQLField(GraphQLList(AddressType), args={'user_id': GraphQLNonNull(GraphQLInt)}, resolve=lambda _, i, user_id: get_user_addresses(user_id)),
    'delivery': GraphQLField(DeliveryType, args={'id': GraphQLNonNull(GraphQLInt)}, resolve=lambda _, i, id: get_delivery(id)),
})

# MUTATION
Mutation = GraphQLObjectType('Mutation', {
    'saveAddress': GraphQLField(GraphQLInt, args={'user_id': GraphQLNonNull(GraphQLInt), 'input': GraphQLNonNull(AddressInput)}, resolve=lambda _, i, user_id, input: save_address(user_id, input)),
    'createDelivery': GraphQLField(GraphQLInt, args={'input': GraphQLNonNull(CreateDeliveryInput)}, resolve=lambda _, i, input: create_delivery(**input)),
    'updateDeliveryStatus': GraphQLField(GraphQLBoolean, args={'delivery_id': GraphQLNonNull(GraphQLInt), 'status': GraphQLNonNull(GraphQLString), 'tracking_code': GraphQLString}, resolve=lambda _, i, **kw: update_delivery_status(**kw)),
})

schema = GraphQLSchema(query=Query, mutation=Mutation)