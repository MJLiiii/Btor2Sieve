(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x7175 (and (distinct s_7 (_ bv255 8)) true)))
(not $x7175)))
(check-sat)
