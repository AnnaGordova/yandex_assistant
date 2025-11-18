package cartModule

import productModule "main/productModule"

type Cart struct{
	CartProducts [] *productModule.Product `json:"products"`
}