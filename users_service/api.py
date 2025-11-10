import graphene

class UserType(graphene.ObjectType):
    id = graphene.ID()
    username = graphene.String()
    number = graphene.String()
USERS = [ 
    {"id": "1", "username": "alice", "number": "1234567890"},
    {"id": "2", "username": "bob", "number": "0987654321"},
]
class Query(graphene.ObjectType):
    users = graphene.List(UserType)

    def resolve_users(self, info):
        return USERS
    def by_id(self,info,id):
        for user in USERS:
            if user["id"] == id:
                return user
        return None
schema = graphene.Schema(query=Query)
    