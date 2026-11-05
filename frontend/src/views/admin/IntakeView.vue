<script setup lang="ts">
import { useMessageState } from '../../composables/useMessageState';
import { reactive, ref } from 'vue';
import AppIcon from '../../components/AppIcon.vue';
import PageHeader from '../../components/PageHeader.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import { createPackage, receiveShipment, verifyShipmentCode } from '../../api/packages';
import type { PackageCreateInput, PackageRecord } from '../../types/api';
import { errorText, formatAppointment } from '../../utils/format';

const defaults = (): PackageCreateInput => ({
  tracking_number: '',
  company: '顺丰速运',
  receiver_name: '',
  receiver_address: '',
  phone: '',
  is_large: false,
  is_fragile: false,
  is_fresh: false,
  is_valuable: false,
});
const form = reactive(defaults());
const saving = ref(false);
const error = useMessageState('error');
const success = useMessageState('success');
const shipmentCode = ref('');
const shipment = ref<PackageRecord>();
const verifying = ref(false);
const receiving = ref(false);
const shipmentError = useMessageState('error');
const shipmentSuccess = useMessageState('success');
async function verifyShipment() {
  if (verifying.value) return;
  shipmentError.value = '';
  shipmentSuccess.value = '';
  shipment.value = undefined;
  if (!/^\d{8}$/.test(shipmentCode.value.trim())) {
    shipmentError.value = '请输入 8 位寄件码';
    return;
  }
  verifying.value = true;
  try {
    shipment.value = await verifyShipmentCode(shipmentCode.value.trim());
  } catch (e) {
    shipmentError.value = errorText(e);
  } finally {
    verifying.value = false;
  }
}
async function confirmShipmentReceipt() {
  if (receiving.value || !shipment.value) return;
  receiving.value = true;
  shipmentError.value = '';
  try {
    if (!shipment.value.shipment_code) throw new Error('订单寄件码已失效，请重新核验');
    shipment.value = await receiveShipment(shipment.value.shipment_code);
    shipmentCode.value = '';
    shipmentSuccess.value = '已核对信息并完成收件入站';
  } catch (e) {
    shipmentError.value = errorText(e);
  } finally {
    receiving.value = false;
  }
}
function reset() {
  Object.assign(form, defaults());
  error.value = '';
}
async function submit() {
  if (saving.value) return;
  error.value = '';
  success.value = '';
  const payload = {
    ...form,
    tracking_number: form.tracking_number.trim(),
    company: form.company.trim(),
    receiver_name: form.receiver_name.trim(),
    receiver_address: form.receiver_address?.trim(),
    phone: form.phone.trim(),
  };
  if (!payload.tracking_number || !payload.company || !payload.receiver_name || !payload.phone) {
    error.value = '请完整填写快递信息和收件人信息';
    return;
  }
  if (!/^1\d{10}$/.test(payload.phone)) {
    error.value = '请输入正确的 11 位收件人手机号';
    return;
  }
  saving.value = true;
  try {
    const created = await createPackage(payload);
    success.value = `运单 ${payload.tracking_number} 已入库，柜位 ${created.cabinet_no}-${created.cabinet_row}，取件码 ${created.pickup_code}。`;
    reset();
  } catch (e) {
    error.value = errorText(e);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <PageHeader title="寄件核验与快递入库" description="核验预约寄件码并收件入站，或登记外部快递。" />

  <section class="panel mb-5">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">预约寄件到站核验</h2>
        <p class="panel-description">核对预约时间、寄收地址和包裹属性后，再确认收件入站</p>
      </div>
      <AppIcon name="scan-line" class="muted" />
    </div>
    <form class="panel-body" @submit.prevent="verifyShipment">
      <label class="field max-w-md"
        >寄件码
        <el-input
          v-model="shipmentCode"
          inputmode="numeric"
          maxlength="8"
          placeholder="输入用户出示的 8 位寄件码"
        />
      </label>
      <div class="form-actions">
        <el-button type="primary" native-type="submit" :loading="verifying">核验寄件码</el-button>
      </div>
      <el-alert
        v-if="shipmentError"
        class="mt-4"
        type="error"
        :title="shipmentError"
        :closable="false"
      />
      <el-alert
        v-if="shipmentSuccess"
        class="mt-4"
        type="success"
        :title="shipmentSuccess"
        :closable="false"
      />
      <div v-if="shipment" class="border-line mt-5 rounded-xl border p-4">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h3 class="panel-title">订单信息核对</h3>
          <StatusBadge :status="shipment.status" :abnormal="shipment.abnormal" />
        </div>
        <dl class="record-details">
          <div>
            <dt>快递公司</dt>
            <dd>{{ shipment.company || '—' }}</dd>
          </div>
          <div>
            <dt>预约到站</dt>
            <dd>
              {{
                formatAppointment(
                  shipment.appointment_date,
                  shipment.appointment_slot,
                  shipment.appointment_at
                )
              }}
            </dd>
          </div>
          <div>
            <dt>寄件人</dt>
            <dd>{{ shipment.sender_name }} · {{ shipment.sender_phone }}</dd>
          </div>
          <div>
            <dt>寄件地址</dt>
            <dd>{{ shipment.sender_address }}</dd>
          </div>
          <div>
            <dt>收件人</dt>
            <dd>{{ shipment.receiver_name }} · {{ shipment.receiver_phone }}</dd>
          </div>
          <div>
            <dt>收件地址</dt>
            <dd>{{ shipment.receiver_address }}</dd>
          </div>
          <div>
            <dt>包裹属性</dt>
            <dd>
              {{
                [
                  shipment.is_large && '大件',
                  shipment.is_fragile && '易碎',
                  shipment.is_fresh && '生鲜冷冻',
                  shipment.is_valuable && '贵重物品',
                ]
                  .filter(Boolean)
                  .join('、') || '普通包裹'
              }}
            </dd>
          </div>
        </dl>
        <div
          v-if="shipment.status === '待揽收' && shipment.shipment_code && !shipment.abnormal"
          class="form-actions justify-end"
        >
          <el-button type="primary" :loading="receiving" @click="confirmShipmentReceipt"
            >信息核对无误，收件入站</el-button
          >
        </div>
        <p v-else-if="shipment.abnormal" class="mt-4 text-sm text-amber-700">
          该订单已标记异常，处理完成后再确认入站。
        </p>
        <p v-else class="mt-4 text-sm text-emerald-700">该寄件订单已完成入站。</p>
      </div>
    </form>
  </section>

  <div class="two-column">
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">登记外部收件快递</h2>
          <p class="panel-description">请核对单号与手机号后提交</p>
        </div>
        <AppIcon name="package-plus" class="muted" />
      </div>
      <form class="panel-body" @submit.prevent="submit">
        <fieldset :disabled="saving" class="m-0 min-w-0 border-0 p-0">
          <div class="form-section">
            <h3><span class="section-number">01</span>快递信息</h3>
            <div class="form-grid">
              <label class="field"
                >快递单号<el-input
                  v-model="form.tracking_number"
                  placeholder="输入面单上的运单号"
                  maxlength="100"
                  required /></label
              ><label class="field"
                >快递公司<el-input
                  v-model="form.company"
                  placeholder="输入快递公司名称"
                  maxlength="50"
                  required
              /></label>
            </div>
          </div>
          <div class="form-section">
            <h3><span class="section-number">02</span>收件人信息</h3>
            <div class="form-grid">
              <label class="field"
                >收件人姓名<el-input
                  v-model="form.receiver_name"
                  placeholder="面单上的收件人姓名"
                  maxlength="50"
                  required /></label
              ><label class="field"
                >收件人手机号<el-input
                  v-model="form.phone"
                  placeholder="11 位手机号码"
                  inputmode="tel"
                  maxlength="11"
                  required
              /></label>
              <label class="field col-span-full"
                >收件地址<el-input
                  v-model="form.receiver_address"
                  placeholder="省、市、区、详细地址"
                  maxlength="200"
              /></label>
            </div>
          </div>
          <div class="form-section">
            <h3><span class="section-number">03</span>包裹属性</h3>
            <div class="flex flex-wrap gap-x-8">
              <el-checkbox v-model="form.is_large">大件物品</el-checkbox
              ><el-checkbox v-model="form.is_fragile">易碎物品</el-checkbox
              ><el-checkbox v-model="form.is_fresh">生鲜冷冻</el-checkbox
              ><el-checkbox v-model="form.is_valuable">贵重物品</el-checkbox>
            </div>
            <p class="panel-description">无特殊属性请忽略此项，勾选后驿站将为您提供针对性服务</p>
            <p class="panel-description">
              系统会自动分配存放柜位，并生成“柜号-排号-四位编号”格式的取件码。
            </p>
          </div>
          <div class="form-actions">
            <el-button type="primary" native-type="submit" :loading="saving"
              ><AppIcon name="check" :size="17" />确认入库</el-button
            ><el-button text :disabled="saving" @click="reset">清空重填</el-button>
          </div>
        </fieldset>
      </form>
    </section>
    <aside class="soft-note">
      <h3 class="flex items-center gap-2"><AppIcon name="scan-line" :size="19" />入库小提示</h3>
      <ol class="hint-list">
        <li>快递单号应与面单保持一致，避免重复登记。</li>
        <li>填写完整的 11 位手机号，系统据此关联收件用户。</li>
        <li>大件、易碎和贵重属性请按实际情况勾选。</li>
      </ol>
      <router-link class="text-link mt-4" to="/admin/packages"
        >查看快递记录<AppIcon name="arrow-right" :size="15"
      /></router-link>
    </aside>
  </div>
</template>
