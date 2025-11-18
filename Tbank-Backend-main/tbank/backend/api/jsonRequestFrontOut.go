package api

import (
	productModule "main/productModule"
	cartModule "main/cartModule"
)

type LoginAnswer struct{
	Token string `json:"token"`
	Message string `json:"message"`
}

type RegisterAnswer struct{
	Token string `json:"token"`
	Message string `json:"message"`
}

type ChangePasswordAnswer struct{
	Message string `json:"message"`
}

type SaveProductInCart struct{
	Message string `json:"message"`
}

type Button struct{
	Text string `json:"text"`
	Value string `json:"value"`
}

type MessageAnswer struct{
	Message string `json:"message"`
	Products []productModule.Product `json:"products"`
	Buttons []Button `json:"buttons"`
}

type FeedbackAnswer struct{
	Success bool `json:"success"`
	Message string `json:"message"`
}

type MessageResponse struct {
    Success bool        `json:"success"`
    Message string      `json:"message"`
}

type GetCartResponse struct{
	Message string `json:"message"`
	Cart cartModule.Cart `json:"cart"`
}

type DeleteProductResponse struct{
	Message string `json:"message"`
}