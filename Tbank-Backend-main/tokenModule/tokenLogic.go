package tokenModule

import (
	loggerModule "main/loggerModule"
	userModule	 "main/userModule"
)


type tokenService struct{
	tokenManager TokenManager
	loggerManager loggerModule.LoggerManager
}

func NewTokenService(tokenManager TokenManager, loggerManager loggerModule.LoggerManager) TokenService{
	return &tokenService{
		tokenManager: tokenManager,
		loggerManager: loggerManager,
	}
}

func (ts *tokenService) GenerateToken(user *userModule.User) (string, error){
	return ts.tokenManager.GenerateToken(user)
}

func (ts *tokenService) VerifyToken(token string) bool{
	return ts.tokenManager.VerifyToken(token)
}

func (ts *tokenService) ExtractClaims(token string) (*UserClaims, error){
	return ts.tokenManager.ExtractClaims(token)
}