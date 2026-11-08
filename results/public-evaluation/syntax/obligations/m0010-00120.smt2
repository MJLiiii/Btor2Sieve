(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x239 (bvsge i_7 (_ bv0 8))))
(not $x239)))
(check-sat)
