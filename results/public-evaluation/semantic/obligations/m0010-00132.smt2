(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1420 (= i_7 (_ bv128 8))))
(not $x1420)))
(check-sat)
