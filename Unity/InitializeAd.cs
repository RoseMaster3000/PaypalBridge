using UnityEngine;
using UnityEngine.Advertisements;
using static UnityEngine.Advertisements.Advertisement;

public class InitializeAd : MonoBehaviour, IUnityAdsInitializationListener
{
    [SerializeField] string _androidGameId;
    [SerializeField] string _iOSGameId;
    [SerializeField] bool _testMode = true;
    private string _gameId;


    private BannerAd bannerAd;
    private InterstitialAd Ad;
    private RewardedAd rewardedAd;

    // we initialize() only once, load() every time we sho() an ad
    void Awake()
    {
        InitializeAds(); //fist initializeng ads

    }

    public void InitializeAds()
    {
#if UNITY_IOS
            _gameId = _iOSGameId;
#elif UNITY_ANDROID
        _gameId = _androidGameId;
#elif UNITY_EDITOR
            _gameId = _androidGameId; //Only for testing the functionality in the Editor
#endif
        if (!Advertisement.isInitialized && Advertisement.isSupported)
        {
            Advertisement.Initialize(_gameId, _testMode, this);
        }
    }


    public void OnInitializationComplete()
    {
        Debug.Log("Unity Ads initialization complete.");

        bannerAd = FindFirstObjectByType<BannerAd>(); // GameMngr
        bannerAd.LoadBanner(); //need to load the ad before showing (every time)

        Ad = FindFirstObjectByType<InterstitialAd>(); //in car controller
        Ad.LoadAd();

        rewardedAd = FindFirstObjectByType<RewardedAd>();
        rewardedAd.LoadAd();

    }

    public void OnInitializationFailed(UnityAdsInitializationError error, string message)
    {
        Debug.Log($"Unity Ads Initialization Failed: {error.ToString()} - {message}");
    }
}