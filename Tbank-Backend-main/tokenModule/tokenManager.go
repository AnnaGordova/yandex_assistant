package tokenModule

import(
	userModule "main/userModule"
)

type UserClaims struct{
	UserID string
	Email string
	ExpiresAt int64
}

type TokenManager interface{
	GenerateToken(user *userModule.User) (string, error)
	VerifyToken(token string) bool
	ExtractClaims(token string)(*UserClaims, error)
}