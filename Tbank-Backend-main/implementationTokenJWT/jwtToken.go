package implementationTokenJWT

import (
	"github.com/golang-jwt/jwt"
	userModule "main/userModule"
	tokenModule "main/tokenModule"
	loggerModule "main/loggerModule"
	"time"
	"fmt"
)

type jwtTokenManager struct{
	secretKey string
	logger loggerModule.LoggerManager

}

func NewJWTTokenManager(secretKey string, logger loggerModule.LoggerManager) tokenModule.TokenManager{
	return &jwtTokenManager{
		secretKey: secretKey,
		logger: logger,
	}
}

type customClaims struct {
    UserID string   `json:"user_id"`
    Email  string   `json:"email"`
    StandardClaims jwt.StandardClaims
}

func (c customClaims) Valid() error {
    return c.StandardClaims.Valid()
}

func (jwtManager *jwtTokenManager) GenerateToken(user *userModule.User) (string, error){
	claims := customClaims{
		UserID: user.ID,
		Email: user.Email,
		StandardClaims: jwt.StandardClaims{
			ExpiresAt: time.Now().Add(30 * time.Minute).Unix(),
            IssuedAt:  time.Now().Unix(),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	jwtManager.logger.INFO("Token Should be Generated")
    return token.SignedString([]byte(jwtManager.secretKey))
}

func (jwtManager *jwtTokenManager) VerifyToken(tokenString string) bool {
    token, err := jwt.ParseWithClaims(tokenString, &customClaims{}, func(token *jwt.Token) (interface{}, error) {
        return []byte(jwtManager.secretKey), nil
    })
    
    if err != nil || !token.Valid {
		jwtManager.logger.ERROR(fmt.Sprintf("Failed validation token : err is %s or just Invaid token", err))
        return false
    }

	jwtManager.logger.INFO("Token Verified successfully")
    return true
}

func (jwtManager *jwtTokenManager) ExtractClaims(tokenString string) (*tokenModule.UserClaims, error) {
    token, err := jwt.ParseWithClaims(tokenString, &customClaims{}, func(token *jwt.Token) (interface{}, error) {
        return []byte(jwtManager.secretKey), nil
    })
    
    if err != nil {
		jwtManager.logger.ERROR(fmt.Sprintf("Failed to extract claims : %s", err))
        return nil, err
    }
    
    if claims, ok := token.Claims.(*customClaims); ok && token.Valid {
		jwtManager.logger.INFO("Successfully extracted claims of token")
        return &tokenModule.UserClaims{
            UserID:    claims.UserID,
            Email:     claims.Email,
			ExpiresAt: claims.StandardClaims.ExpiresAt,
        }, nil
    }

	jwtManager.logger.ERROR("Failed to extract claims : bad token")
    return nil, jwt.ErrInvalidKey
}