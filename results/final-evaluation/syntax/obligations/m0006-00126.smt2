(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x7175 (bvule s_3 (_ bv8 4))))
(not $x7175)))
(check-sat)
