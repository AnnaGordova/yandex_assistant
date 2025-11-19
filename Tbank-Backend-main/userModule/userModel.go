package userModule

type User struct{
	ID string
	Email string `json:"email" validate: "required,email"`
	Password string `json:"password" validate:"required,min=8,max=100"`
}