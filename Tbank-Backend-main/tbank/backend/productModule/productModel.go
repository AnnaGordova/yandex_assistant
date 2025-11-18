package productModule

type Product struct{
	ID int64 `json:"id"`
	Name string `json:"name"`
	Link string `json:"link"`
	Description string `json:"description"`
	Price float64 `json:"price"`
	Picture string `json:"picture"`
	Rating float64 `json:"rating"`
	AmmountOfReviews int64 `json:"ammountOfReviews"`
	Size string `json:"size"`
	CountOfProduct int64 `json:"countOfProduct"`
}