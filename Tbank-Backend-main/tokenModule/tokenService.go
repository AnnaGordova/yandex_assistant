package tokenModule

import(
	userModule "main/userModule"
)

type TokenService interface{
	GenerateToken(user *userModule.User) (string, error)
	VerifyToken(token string) bool
	ExtractClaims(token string)(*UserClaims, error)
}