
class CVPartnerUser:
    def __init__(self, user_id, name, email, cv_id, updated_at):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.cv_id = cv_id
        self.updated_at = updated_at

    def __str__(self):
        return self.user_id + " " + self.name + " " + self.email + " " + self.cv_id + " " + self.updated_at.__str__()
