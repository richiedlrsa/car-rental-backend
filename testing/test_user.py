from backend.user import hash_password, verify_password

class TestUserAuth:
    def test_password_verification(self):
        hashed_pwd = hash_password('test_password')
        assert verify_password('test_password', hashed_pwd)
        assert not verify_password('wrong_password', hashed_pwd)
        assert isinstance(hashed_pwd, str)