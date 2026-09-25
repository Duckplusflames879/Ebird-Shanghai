(function () {
  const FALLBACK = {
    appearance: '现场观察时结合整体轮廓、羽色、头部、喙形、翼纹、尾形和腿脚颜色综合判断。',
    behavior: '记录活动层位、移动方式、觅食动作以及是否成群，有助于识别和积累个人观察经验。',
    habitat: '结合现场水体、植被、地表类型和开阔程度记录其出现环境。',
    diet: '结合觅食对象和觅食动作记录，可用于辅助判断其生态类型。',
    migration: '上海的出现季节以本地名录资料为基础；观察时建议同时记录日期，以形成个人季节记录。'
  };

  function getLocal(bird) {
    const base = (window.BIRD_DETAILS && window.BIRD_DETAILS[bird.id]) || {};
    return {
      ...FALLBACK,
      ...base,
      family: bird.family,
      genus: bird.genus && bird.genus !== '—' ? bird.genus : (base.genus || '未提供属级信息')
    };
  }

  window.BirdProfiles = { getLocal };
})();
