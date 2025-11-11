# users_service/schemas.py
from graphql import (
    GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString,
    GraphQLInt, GraphQLList, GraphQLNonNull, GraphQLInputObjectType,
    GraphQLInputField, GraphQLBoolean
)
from repository import get_user, get_users, create_user, add_to_wishlist, get_wishlist

# USER TYPE
UserType = GraphQLObjectType('User', {
    'id': GraphQLField(GraphQLInt),
    'username': GraphQLField(GraphQLString),
    'name': GraphQLField(GraphQLString),
    'email': GraphQLField(GraphQLString),
    'phone_number': GraphQLField(GraphQLString),
    'role': GraphQLField(GraphQLString),
    'status': GraphQLField(GraphQLString),
    'points': GraphQLField(GraphQLInt),
    'tier': GraphQLField(GraphQLString),
})

# INPUT TYPE (GraphQLInputField!)
CreateUserInput = GraphQLInputObjectType('CreateUserInput', {
    'username': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'name': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'email': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'phone_number': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'password': GraphQLInputField(GraphQLNonNull(GraphQLString)),
    'role': GraphQLInputField(GraphQLString),  # default: customer
})

# QUERY
Query = GraphQLObjectType('Query', {
    'me': GraphQLField(UserType, resolve=lambda _, info: info.context.get('user')),
    'users': GraphQLField(GraphQLList(UserType), resolve=lambda *_: get_users()),
    'user': GraphQLField(
        UserType,
        args={'id': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, id: get_user(id)
    ),
    'wishlist': GraphQLField(
        GraphQLList(GraphQLInt),
        resolve=lambda _, info: get_wishlist(info.context['user']['id']) if info.context.get('user') else []
    ),
})

# MUTATION
Mutation = GraphQLObjectType('Mutation', {
    'createUser': GraphQLField(
        UserType,
        args={'input': GraphQLNonNull(CreateUserInput)},
        resolve=lambda _, info, input: create_user(input)
    ),
    'addToWishlist': GraphQLField(
        GraphQLBoolean,
        args={'productId': GraphQLNonNull(GraphQLInt)},
        resolve=lambda _, info, productId: add_to_wishlist(info.context['user']['id'], productId)
    ),
})

# SCHEMA
schema = GraphQLSchema(query=Query, mutation=Mutation)