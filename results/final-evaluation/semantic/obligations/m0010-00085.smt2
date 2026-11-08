(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x4991 (= i_4 (_ bv2147483648 32))))
(not $x4991)))
(check-sat)
