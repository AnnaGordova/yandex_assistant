package api

import (
	loggerModule "main/loggerModule"
	databaseModule "main/databaseModule"
	tokenModule "main/tokenModule"
	// productModule "main/productModule"
	mlModule "main/mlModule"
	"encoding/json"
	"net/http"
	"errors"
	"strings"
	//"time"
	//"fmt"
)

type MessageHandler interface{
	SaveProduct(http.ResponseWriter, *http.Request) (SaveProductInCart, error)
	DeleteProduct(http.ResponseWriter, *http.Request) (DeleteProductResponse, error)
	GetCart(http.ResponseWriter, *http.Request) (GetCartResponse, error)
 	IterMessage(http.ResponseWriter, *http.Request) (MessageAnswer, error)
}

type messageHandler struct{
	tokenService tokenModule.TokenService
	databaseService databaseModule.DatabaseService
	loggerService loggerModule.LoggerService
	mlService mlModule.MLService

}

func NewMessageHandler(tokenService tokenModule.TokenService, databaseService databaseModule.DatabaseService, mlService mlModule.MLService, loggerService loggerModule.LoggerService) MessageHandler{
	return &messageHandler{
		tokenService: tokenService,
		databaseService: databaseService,
		loggerService: loggerService,
		mlService: mlService,
	}
}

func(mh *messageHandler) SaveProduct(writer http.ResponseWriter, request *http.Request)(SaveProductInCart, error){
	var answer SaveProductInCart
	var message LikeProduct
	if err:= json.NewDecoder(request.Body).Decode(&message); err!=nil{
		mh.loggerService.WARNING("Failed to read product")
		answer.Message = "Failed to read product"
		sendError(writer, "INVALID JSON" + err.Error(), http.StatusBadRequest)
		return answer, err
	}

	product := message.Product
	mh.loggerService.INFO("Trying to save product")
	isOk := mh.tokenService.VerifyToken(message.Token)

	if !isOk{
		mh.loggerService.WARNING("Token is invalid in change password")
		answer.Message = "Session is over"
		return answer, errors.New("Session is over")
	}

	claims, err := mh.tokenService.ExtractClaims(message.Token)

	if err!=nil{
		mh.loggerService.WARNING("Failed to extract claims")
		answer.Message = "Youre doing something nasty"
		return answer, err
	}

	user, err := mh.databaseService.FindUser(claims.Email)
	if err!=nil{
		return answer, err
	}

	_, err = mh.databaseService.StoreProduct(&product)
	if err!=nil{
		mh.loggerService.INFO("Failed to store product")
		answer.Message = "Failed to save product"
		return answer, err
	}

	err = mh.databaseService.AddToCart(user, &product, product.CountOfProduct)
	if err!= nil{
		mh.loggerService.INFO("Failed to add to Cart")
		answer.Message = "Failed to save product"
		return answer, err
	}

	answer.Message = "Product was saved"
	return answer, nil
}


func(mh *messageHandler) IterMessage(writer http.ResponseWriter, request *http.Request)(MessageAnswer, error){
	var message MessageRequest
	var answer MessageAnswer

	if err:= json.NewDecoder(request.Body).Decode(&message); err!=nil{
		mh.loggerService.WARNING("Failed to read message")
		answer.Message = "Failed to read message"
		sendError(writer, "INVALID JSON" + err.Error(), http.StatusBadRequest)
		return answer, err
	}

	mh.loggerService.INFO("Trying to get message from frontend")

	ok := mh.tokenService.VerifyToken(message.Token)
	if !ok{
		mh.loggerService.WARNING("Token is invalid in Message handling")
		answer.Message = "Bad Message"
		return answer, errors.New("Bad Message")
	}

	jsonBytes, err := json.Marshal(message)
    if err != nil {
        mh.loggerService.WARNING("Failed to Marshal to json Message")
		answer.Message = "Bad Message request"
		return answer, err
    }

	jsonString := string(jsonBytes)

	mlAnswer, err := mh.mlService.Send(jsonString)
	if err!=nil{
		panic("No connection to ML")
	}

	if err:= json.NewDecoder(strings.NewReader(mlAnswer)).Decode(&answer); err!=nil{
		mh.loggerService.WARNING("Failed to read product")
		answer.Message = "Failed to read product"
		sendError(writer, "INVALID JSON" + err.Error(), http.StatusBadRequest)
		return answer, err
	}
	return answer, nil
}


func (mh *messageHandler) GetCart(writer http.ResponseWriter, request *http.Request)(GetCartResponse, error){
	var message GetCartRequest
	var answer GetCartResponse

	if err:= json.NewDecoder(request.Body).Decode(&message); err!=nil{
		mh.loggerService.WARNING("Failed to read get cart request")
		answer.Message = "Failed to read your message"
		sendError(writer, "INVALID JSON" + err.Error(), http.StatusBadRequest)
		return answer, err
	}

	mh.loggerService.INFO("Trying to send cart to frontend")

	ok := mh.tokenService.VerifyToken(message.Token)
	if !ok{
		mh.loggerService.WARNING("Token is invalid in Cart get handling")
		answer.Message = "Bad Request"
		return answer, errors.New("Bad Request")
	}


	claims, err := mh.tokenService.ExtractClaims(message.Token)

	if err!=nil{
		mh.loggerService.WARNING("Failed to extract claims")
		answer.Message = "Youre doing something nasty"
		return answer, err
	}

	user, err := mh.databaseService.FindUser(claims.Email)
	
	if err!=nil{
		answer.Message = "Error with your account"
		return answer, err
	}

	cart, err := mh.databaseService.GetCart(user)

	if err!=nil{
		answer.Message = "Cart is empty"
		return answer, err
	}

	answer.Message = "Cart returning"
	answer.Cart = *cart
	return answer, nil
}

func (mh *messageHandler) DeleteProduct(writer http.ResponseWriter, request *http.Request) (DeleteProductResponse, error){
	var message DeleteProductRequest
	var answer DeleteProductResponse

	if err:= json.NewDecoder(request.Body).Decode(&message); err!=nil{
		mh.loggerService.WARNING("Failed to read delete product request")
		answer.Message = "Failed to delete item"
		sendError(writer, "INVALID JSON" + err.Error(), http.StatusBadRequest)
		return answer, err
	}

	mh.loggerService.INFO("Trying to delete product")

	ok := mh.tokenService.VerifyToken(message.Token)
	if !ok{
		mh.loggerService.WARNING("Token is invalid in delete product")
		answer.Message = "Bad Request"
		return answer, errors.New("Bad Request")
	}

	claims, err := mh.tokenService.ExtractClaims(message.Token)
	if err!=nil{
		mh.loggerService.WARNING("Failed to extract claims")
		answer.Message = "Youre doing something nasty"
		return answer, err
	}

	user, err := mh.databaseService.FindUser(claims.Email)
	
	if err!=nil{
		answer.Message = "Error with your account"
		return answer, err
	}

	err = mh.databaseService.DeleteProduct(&message.Product, user)
	if err!=nil{
		answer.Message = "Error while delete product"
		return answer, err
	}

	answer.Message = "Product deleted!"
	return answer, nil

	

}
