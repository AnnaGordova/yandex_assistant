package api

import productModule "main/productModule"

type LoginRequest struct{
	Email string `json:"email"`
	Password string `json:"password"`
}

type RegisterRequest struct{
	Name string `json:"name"`
	Email string `json:"email"`
	Password string `json:"password"`
}

type PasswordChangeRequest struct{
	Email string `json:"email"`
	Token string `json:"token"`
	Password string `json:"password"`
}

type MessageParams struct{
	Address string `json:"address"`
	Budget string `json:"budget"`
	Wishes string `json:"wishes"`
}

type ChatStory struct{
	Text string `json:"text"`
	IsUser bool `json:"isUser"`
}

type MessageRequest struct {
	Email string `json:"email"`
	Message string `json:"message"`
	Token string `json:"token"`
	Params MessageParams `json:"params"`
	ChatHistory []ChatStory `json:"chatHistory"`
}

type LikeProduct struct{
	Product productModule.Product `json:"product"`
	Token string `json:"token"`
	feedback string `json:"feedback"`
}

type GetCartRequest struct{
	Token string `json:"token"`
}

type DeleteProductRequest struct{
	Token string `json:"token"`
	Product productModule.Product `json:"id"`
}