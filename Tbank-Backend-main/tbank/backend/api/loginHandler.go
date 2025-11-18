package api

import (
	userModule "main/userModule"
	loggerModule "main/loggerModule"
	databaseModule "main/databaseModule"
	tokenModule "main/tokenModule"
	"encoding/json"
	"net/http"
	"fmt"
	"errors"
)

type LoginHandler interface{
	Register(http.ResponseWriter, *http.Request) (RegisterAnswer, error)
	Login(http.ResponseWriter, *http.Request) (LoginAnswer, error)
	ChangePassword(http.ResponseWriter, *http.Request) (ChangePasswordAnswer, error)
}

type loginHandler struct{
	tokenService tokenModule.TokenService
	databaseService databaseModule.DatabaseService
	loggerService loggerModule.LoggerService
}

func NewLoginHandler(tokenService tokenModule.TokenService, databaseService databaseModule.DatabaseService, loggerService loggerModule.LoggerService) LoginHandler{
	return &loginHandler{
		tokenService: tokenService,
		databaseService: databaseService,
		loggerService: loggerService,
	}
}

func(lh *loginHandler) Register(writer http.ResponseWriter, request *http.Request) (RegisterAnswer, error){
	// TODO: ALL VALIDATION AND CHECKS
	var message RegisterRequest
	var registerAnswer RegisterAnswer
	if err:= json.NewDecoder(request.Body).Decode(&message); err!=nil{
		lh.loggerService.WARNING("Failed to decode Register JSON")
		registerAnswer.Token = ""
		registerAnswer.Message = "Failed to register user!"
		sendError(writer, "INVALID JSON" + err.Error(), http.StatusBadRequest)
		return registerAnswer, err
	}

	lh.loggerService.INFO(fmt.Sprintf("Trying to register user %s ", message.Email))	

	user := &userModule.User{ID: "", Email: message.Email, Password: message.Password}
	token, err := lh.tokenService.GenerateToken(user)
	if err!=nil{
		lh.loggerService.WARNING("Failed to register user in token Generation")
		registerAnswer.Token = ""
		registerAnswer.Message = "Failed to register user!"
		return registerAnswer, err
	}

	err = lh.databaseService.StoreUser(user)
	if err!=nil{
		lh.loggerService.WARNING("Failed to register user in Database saving")
		registerAnswer.Token = ""
		registerAnswer.Message = "Failed to register user!"
		return registerAnswer, err
	}

	registerAnswer.Token = token
	registerAnswer.Message = "User added!"
	return registerAnswer, nil
}

func(lh *loginHandler) Login(writer http.ResponseWriter, request *http.Request) (LoginAnswer, error){
	// TODO: ALL VALIDATION AND 
	var message LoginRequest
	var loginAnswer LoginAnswer
	if err:= json.NewDecoder(request.Body).Decode(&message); err!=nil{
		lh.loggerService.WARNING("Failed to parse Login JSON")
		loginAnswer.Token = ""
		loginAnswer.Message = "Invalid login or password"
		sendError(writer, "INVALID JSON" + err.Error(), http.StatusBadRequest)
		return loginAnswer, err
	}

	lh.loggerService.INFO("Trying to Login user")
	
	real_user, err := lh.databaseService.FindUser(message.Email)
	if err!=nil{
		lh.loggerService.WARNING("Failed to find user in database")
		loginAnswer.Token = ""
		loginAnswer.Message = "Invalid login or password"
		return loginAnswer, err
	}

	if message.Email == real_user.Email && message.Password == real_user.Password{
		token, err := lh.tokenService.GenerateToken(real_user)
		if err!=nil{
			lh.loggerService.WARNING("Failed to generate token")
			loginAnswer.Token = ""
			loginAnswer.Message = "Invalid login or password"
			return loginAnswer, err
		}

		loginAnswer.Token = token
		loginAnswer.Message = "Login finished OK"
		return loginAnswer, nil
	}

	lh.loggerService.WARNING("Failed to verify user")
	loginAnswer.Token = ""
	loginAnswer.Message = "Invalid login or password"
	return loginAnswer, err
}

func(lh *loginHandler) ChangePassword(writer http.ResponseWriter, request *http.Request) (ChangePasswordAnswer, error){
	var message PasswordChangeRequest
	var changePasswordAnswer ChangePasswordAnswer
	if err:= json.NewDecoder(request.Body).Decode(&message); err!=nil{
		lh.loggerService.WARNING("Failed to parse ChangePassword JSON")
		changePasswordAnswer.Message = "Invalid request to Change Password"
		sendError(writer, "INVALID JSON" + err.Error(), http.StatusBadRequest)
		return changePasswordAnswer, err
	}

	lh.loggerService.INFO("Trying to change password for user")

	isOk := lh.tokenService.VerifyToken(message.Token)

	if !isOk{
		lh.loggerService.WARNING("Token is invalid in change password")
		changePasswordAnswer.Message = "Session is over"
		return changePasswordAnswer, errors.New("Session is over")
	}

	claims, err := lh.tokenService.ExtractClaims(message.Token)

	if err!=nil{
		lh.loggerService.WARNING("Failed to extract claims")
		changePasswordAnswer.Message = "Youre doing something nasty"
		return changePasswordAnswer, err
	}

	if message.Email != claims.Email{
		lh.loggerService.WARNING("Failed to extract claims")
		changePasswordAnswer.Message = "Youre doing something sooo nasty. We will investigate this later"
		return changePasswordAnswer, err
	} else {
		user := &userModule.User{ID: claims.UserID, Email: claims.Email, Password: message.Password}
		err := lh.databaseService.ChangePassword(user)

		if err!=nil{
			lh.loggerService.WARNING("Failed to save new password")
			changePasswordAnswer.Message = "Bad Password"
			return changePasswordAnswer, err
		}

		changePasswordAnswer.Message = "Password was changed"
		return changePasswordAnswer, nil
	}
}